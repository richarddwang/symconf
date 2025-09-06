"""TwinConf parser implementation."""

import argparse
import copy
import importlib
import inspect
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from dotenv import load_dotenv

from .config import ConfigurationObject


class TwinConfParser:
    """The main TwinConf parser for handling configuration files and command line arguments.

    This parser handles:
    - Reading and merging YAML files
    - Loading dotenv files
    - Command line argument parsing
    - Configuration validation
    - Variable and expression interpolation
    """

    def __init__(
        self,
        base_classes: Optional[Dict[str, type]] = None,
        validate_types: bool = True,
        check_missing_args: bool = True,
        check_unexpected_args: bool = True,
    ) -> None:
        """Initialize the TwinConf parser.

        Args:
            base_classes: Dictionary mapping configuration keys to their base classes for validation
            validate_types: Whether to validate argument types against type annotations
            check_missing_args: Whether to check for missing required arguments
            check_unexpected_args: Whether to check for unexpected arguments
        """
        self.base_classes = base_classes or {}
        self.validate_types = validate_types
        self.check_missing_args = check_missing_args
        self.check_unexpected_args = check_unexpected_args

        self._setup_argument_parser()

    def _setup_argument_parser(self) -> None:
        """Set up the argument parser."""
        self.parser = argparse.ArgumentParser(description="TwinConf Configuration Parser")
        self.parser.add_argument("config_files", nargs="*", help="YAML configuration files to load")
        self.parser.add_argument("--env", nargs="*", default=[], help="Dotenv files to load")
        self.parser.add_argument("--args", nargs="*", default=[], help="Configuration overrides in key=value format")
        self.parser.add_argument(
            "--print", action="store_true", help="Print the final configuration and wait for confirmation"
        )
        self.parser.add_argument("--help-object", type=str, help="Show help for a specific object")
        self.parser.add_argument("--sweep", nargs="+", help="Parameter sweep configuration")

    def parse_args(self, args: Optional[List[str]] = None) -> Union[ConfigurationObject, List[ConfigurationObject]]:
        """Parse arguments and return configuration object(s).

        Args:
            args: Optional list of arguments (defaults to sys.argv)

        Returns:
            Configuration object or list of configuration objects for sweeps
        """
        if args is None:
            args = sys.argv[1:]

        parsed_args = self.parser.parse_args(args)

        # Handle help for specific objects
        if getattr(parsed_args, "help_object", None):
            self._show_object_help(parsed_args.help_object)
            sys.exit(0)

        # Handle sweeps
        if parsed_args.sweep:
            return self._handle_sweep(parsed_args)

        # Normal configuration parsing
        config = self._parse_single_config(parsed_args)

        # Print configuration if requested
        if parsed_args.print:
            self._print_and_confirm(config)

        return config

    def _parse_single_config(self, parsed_args: argparse.Namespace) -> ConfigurationObject:
        """Parse a single configuration."""
        # Step 1: Load dotenv files
        for env_file in parsed_args.env:
            load_dotenv(env_file)

        # Step 2: Load and merge YAML files
        config_data = {}
        for config_file in parsed_args.config_files:
            file_data = self._load_yaml_file(config_file)
            config_data = self._deep_merge(config_data, file_data)

        # Step 3: Process MERGE keywords
        config_data = self._process_merge_keywords(config_data, os.getcwd())

        # Step 4: Apply command line overrides
        config_data = self._apply_cli_overrides(config_data, parsed_args.args)

        # Step 5: Remove REMOVE keywords
        config_data = self._process_remove_keywords(config_data)

        # Create configuration object
        config = ConfigurationObject(config_data)

        # Step 6: Apply default values
        config = self._apply_default_values(config)

        # Step 7: Process interpolations
        config = self._process_interpolations(config)

        # Step 8: Validate configuration
        if self.validate_types or self.check_missing_args or self.check_unexpected_args:
            self._validate_configuration(config)

        return config

    def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """Load a YAML file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {file_path}: {e}")

    def _deep_merge(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        from .utils import apply_list_merges

        result = copy.deepcopy(dict1)

        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Check for LIST type special handling
                if result[key].get("TYPE") == "LIST" or value.get("TYPE") == "LIST":
                    result[key] = apply_list_merges(result[key], value)
                else:
                    result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)

        return result

    def _process_merge_keywords(self, config_data: Dict[str, Any], base_path: str) -> Dict[str, Any]:
        """Process MERGE keywords in configuration."""
        if isinstance(config_data, dict):
            result = {}

            # Process MERGE at current level first
            if "MERGE" in config_data:
                merge_path = config_data["MERGE"]
                merged_data = self._load_merge_data(merge_path, base_path)
                result = self._deep_merge(result, merged_data)

            # Process other keys, merging them into result
            for key, value in config_data.items():
                if key == "MERGE":
                    continue

                if isinstance(value, dict):
                    # Recursively process nested dictionaries
                    processed_value = self._process_merge_keywords(value, base_path)
                    # Merge with existing result
                    if key in result and isinstance(result[key], dict):
                        result[key] = self._deep_merge(result[key], processed_value)
                    else:
                        result[key] = processed_value
                else:
                    result[key] = value

            return result

        return config_data

    def _load_merge_data(self, merge_path: str, base_path: str) -> Dict[str, Any]:
        """Load data from a MERGE path."""
        # Split path and nested keys
        if "." in merge_path:
            parts = merge_path.split(".")
            file_part = parts[0]
            nested_keys = parts[1:]
        else:
            file_part = merge_path
            nested_keys = []

        # Load the file
        if not file_part.endswith(".yaml") and not file_part.endswith(".yml"):
            file_part += ".yaml"

        file_path = Path(base_path) / file_part
        if not file_path.exists():
            file_path = Path(base_path) / f"{file_part}.yaml"

        data = self._load_yaml_file(str(file_path))

        # Navigate to nested keys
        for key in nested_keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                raise KeyError(f"Key '{key}' not found in merge path '{merge_path}'")

        return data

    def _apply_cli_overrides(self, config_data: Dict[str, Any], args: List[str]) -> Dict[str, Any]:
        """Apply command line overrides."""
        result = copy.deepcopy(config_data)

        for arg in args:
            if "=" not in arg:
                raise ValueError(f"Invalid argument format: {arg}. Expected key=value")

            key_path, value_str = arg.split("=", 1)
            keys = key_path.split(".")

            # Parse the value
            value = self._parse_value(value_str)

            # Navigate and set the value
            current = result
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]

            current[keys[-1]] = value

        return result

    def _parse_value(self, value_str: str) -> Any:
        """Parse a string value to appropriate Python type."""
        # Try to parse as YAML for complex types
        try:
            return yaml.safe_load(value_str)
        except yaml.YAMLError:
            # Return as string if YAML parsing fails
            return value_str

    def _process_remove_keywords(self, config_data: Any) -> Any:
        """Remove keys marked with REMOVE keyword."""
        if isinstance(config_data, dict):
            result = {}
            for key, value in config_data.items():
                if value == "REMOVE":
                    continue  # Skip this key
                else:
                    result[key] = self._process_remove_keywords(value)
            return result
        elif isinstance(config_data, list):
            return [self._process_remove_keywords(item) for item in config_data]
        else:
            return config_data

    def _apply_default_values(self, config: ConfigurationObject) -> ConfigurationObject:
        """Apply default values for TYPE-specified objects."""
        return self._apply_defaults_recursive(config)

    def _apply_defaults_recursive(self, obj: Any) -> Any:
        """Recursively apply default values."""
        if isinstance(obj, ConfigurationObject):
            if "TYPE" in obj:
                # This is an object configuration, apply defaults
                obj_type = obj["TYPE"]
                if isinstance(obj_type, str):
                    try:
                        actual_type = self._import_object(obj_type)
                        defaults = self._get_default_values(actual_type)

                        # Apply defaults for missing keys
                        for key, default_value in defaults.items():
                            if key not in obj:
                                obj[key] = default_value
                    except ImportError:
                        pass  # Skip if object can't be imported

            # Recursively process nested objects
            for key, value in obj.items():
                obj[key] = self._apply_defaults_recursive(value)

        elif isinstance(obj, list):
            return [self._apply_defaults_recursive(item) for item in obj]

        return obj

    def _get_default_values(self, obj_type: Any) -> Dict[str, Any]:
        """Get default values for an object's parameters."""
        defaults = {}

        try:
            if inspect.isclass(obj_type):
                signature = inspect.signature(obj_type.__init__)
            elif callable(obj_type):
                signature = inspect.signature(obj_type)
            else:
                return defaults

            for param_name, param in signature.parameters.items():
                if param_name in ("self", "cls"):
                    continue

                if param.default != inspect.Parameter.empty:
                    defaults[param_name] = param.default

        except (TypeError, ValueError):
            pass  # Skip if signature inspection fails

        return defaults

    def _process_interpolations(self, config: ConfigurationObject) -> ConfigurationObject:
        """Process variable and expression interpolations."""
        # Multiple passes to resolve nested interpolations
        max_iterations = 10
        for i in range(max_iterations):
            old_config = copy.deepcopy(config)
            config = self._resolve_interpolations_recursive(config, config)

            # Check if anything changed
            if self._configs_equal(old_config, config):
                break
        else:
            # If we reach here, we might have circular references
            # But we'll return the config anyway
            pass

        return config

    def _configs_equal(self, config1: Any, config2: Any) -> bool:
        """Check if two configurations are equal (for detecting convergence)."""
        if not isinstance(config1, type(config2)) and not isinstance(config2, type(config1)):
            return False

        if isinstance(config1, ConfigurationObject):
            if set(config1.keys()) != set(config2.keys()):
                return False
            return all(self._configs_equal(config1[key], config2[key]) for key in config1.keys())
        elif isinstance(config1, list):
            if len(config1) != len(config2):
                return False
            return all(self._configs_equal(config1[i], config2[i]) for i in range(len(config1)))
        else:
            return config1 == config2

    def _resolve_interpolations_recursive(self, obj: Any, root_config: Any) -> Any:
        """Recursively resolve interpolations."""
        if isinstance(obj, ConfigurationObject):
            result = ConfigurationObject()
            for key, value in obj.items():
                result[key] = self._resolve_interpolations_recursive(value, root_config)
            return result

        elif isinstance(obj, list):
            return [self._resolve_interpolations_recursive(item, root_config) for item in obj]

        elif isinstance(obj, str):
            # First resolve variables
            result = self._interpolate_string(obj, root_config)
            # Then resolve expressions if result is still a string
            if isinstance(result, str):
                result = self._interpolate_expressions(result, root_config)
            return result

        else:
            return obj

    def _interpolate_string(self, text: str, config: Any) -> Any:
        """Interpolate variables in a string."""
        pattern = re.compile(r"\$\{([^}]+)\}")

        def replace_var(match):
            var_name = match.group(1).strip()

            # Check if it's an expression (contains backticks)
            if "`" in var_name:
                return match.group(0)  # Leave for expression interpolation

            # Try to resolve from config
            try:
                value = self._get_nested_value(config, var_name)
                return str(value)
            except KeyError:
                # Try environment variables
                env_value = os.getenv(var_name)
                if env_value is not None:
                    return env_value

                raise KeyError(f"Variable '{var_name}' not found in configuration or environment")

        # Check if the entire string is a single variable reference
        full_match = pattern.fullmatch(text)
        if full_match:
            var_name = full_match.group(1).strip()
            if "`" not in var_name:
                try:
                    return self._get_nested_value(config, var_name)
                except KeyError:
                    env_value = os.getenv(var_name)
                    if env_value is not None:
                        # Try to parse as appropriate type
                        return self._parse_value(env_value)
                    raise KeyError(f"Variable '{var_name}' not found in configuration or environment")

        # Replace all variables in the string
        return pattern.sub(replace_var, text)

    def _interpolate_expressions(self, text: str, config: Any) -> Any:
        """Interpolate expressions in a string."""
        pattern = re.compile(r"\$\{([^}]*`[^}]*)\}")

        def replace_expr(match):
            expr = match.group(1)

            # Replace `var` with actual values
            var_pattern = re.compile(r"`([^`]+)`")

            def replace_var_in_expr(var_match):
                var_name = var_match.group(1)
                try:
                    value = self._get_nested_value(config, var_name)
                    return repr(value)
                except KeyError:
                    env_value = os.getenv(var_name)
                    if env_value is not None:
                        return repr(self._parse_value(env_value))
                    raise KeyError(f"Variable '{var_name}' not found in expression")

            resolved_expr = var_pattern.sub(replace_var_in_expr, expr)

            # Evaluate the expression
            try:
                result = eval(resolved_expr, {"__builtins__": {}}, {})  # noqa: S307
                return str(result)
            except Exception as e:
                raise ValueError(f"Error evaluating expression '{expr}': {e}")

        # Check if the entire string is a single expression
        full_match = pattern.fullmatch(text)
        if full_match:
            expr = full_match.group(1)
            var_pattern = re.compile(r"`([^`]+)`")

            def replace_var_in_expr(var_match):
                var_name = var_match.group(1)
                try:
                    return self._get_nested_value(config, var_name)
                except KeyError:
                    env_value = os.getenv(var_name)
                    if env_value is not None:
                        return self._parse_value(env_value)
                    raise KeyError(f"Variable '{var_name}' not found in expression")

            resolved_expr = var_pattern.sub(lambda m: repr(replace_var_in_expr(m)), expr)

            try:
                return eval(resolved_expr, {"__builtins__": {}}, {})  # noqa: S307
            except Exception as e:
                raise ValueError(f"Error evaluating expression '{expr}': {e}")

        # Replace expressions in the string
        return pattern.sub(replace_expr, text)

    def _get_nested_value(self, obj: Any, key_path: str) -> Any:
        """Get a nested value using dot notation."""
        keys = key_path.split(".")
        current = obj

        for key in keys:
            if isinstance(current, (dict, ConfigurationObject)):
                if key in current:
                    current = current[key]
                else:
                    raise KeyError(f"Key '{key}' not found")
            else:
                raise KeyError(f"Cannot access key '{key}' on non-dict object")

        return current

    def _validate_configuration(self, config: ConfigurationObject) -> None:
        """Validate the configuration."""
        errors = []

        self._validate_recursive(config, "", errors)

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(errors)
            raise ValueError(error_msg)

    def _validate_recursive(self, obj: Any, path: str, errors: List[str]) -> None:
        """Recursively validate configuration objects."""
        if isinstance(obj, ConfigurationObject) and "TYPE" in obj:
            self._validate_object_config(obj, path, errors)

        elif isinstance(obj, ConfigurationObject):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                self._validate_recursive(value, new_path, errors)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                self._validate_recursive(item, new_path, errors)

    def _validate_object_config(self, config: ConfigurationObject, path: str, errors: List[str]) -> None:
        """Validate a single object configuration."""
        obj_type = config["TYPE"]

        try:
            if isinstance(obj_type, str):
                actual_type = self._import_object(obj_type)
            else:
                actual_type = obj_type

            # Get signature
            if inspect.isclass(actual_type):
                signature = inspect.signature(actual_type.__init__)
            elif callable(actual_type):
                signature = inspect.signature(actual_type)
            else:
                return

            # Validate arguments
            self._validate_object_args(config, signature, actual_type, path, errors)

        except ImportError as e:
            errors.append(f"{path}: Cannot import object type '{obj_type}': {e}")
        except Exception as e:
            errors.append(f"{path}: Error validating object: {e}")

    def _validate_object_args(
        self, config: ConfigurationObject, signature: inspect.Signature, obj_type: Any, path: str, errors: List[str]
    ) -> None:
        """Validate object arguments against signature."""
        # Get provided arguments (excluding special keys)
        provided_args = set(config.kwargs.keys())

        # Get signature parameters
        sig_params = {}
        required_params = set()

        for param_name, param in signature.parameters.items():
            if param_name in ("self", "cls"):
                continue

            sig_params[param_name] = param

            if param.default == inspect.Parameter.empty and param.kind != param.VAR_KEYWORD:
                required_params.add(param_name)

        # Check for missing required arguments
        if self.check_missing_args:
            missing = required_params - provided_args
            for missing_arg in missing:
                errors.append(f"{path}: Missing required argument '{missing_arg}'")

        # Check for unexpected arguments
        if self.check_unexpected_args:
            has_var_keyword = any(p.kind == p.VAR_KEYWORD for p in signature.parameters.values())
            if not has_var_keyword:
                unexpected = provided_args - set(sig_params.keys())
                for unexpected_arg in unexpected:
                    errors.append(f"{path}: Unexpected argument '{unexpected_arg}'")

        # Validate argument types
        if self.validate_types:
            self._validate_argument_types(config, sig_params, path, errors)

    def _validate_argument_types(
        self, config: ConfigurationObject, sig_params: Dict[str, inspect.Parameter], path: str, errors: List[str]
    ) -> None:
        """Validate argument types."""
        # This is a simplified type validation - a full implementation would be more complex
        for arg_name, value in config.kwargs.items():
            if arg_name in sig_params:
                param = sig_params[arg_name]
                if param.annotation != inspect.Parameter.empty:
                    # Basic type checking - this could be expanded significantly
                    expected_type = param.annotation
                    if not self._is_compatible_type(value, expected_type):
                        errors.append(
                            f"{path}.{arg_name}: Expected type {expected_type}, "
                            f"got {type(value).__name__} with value {value!r}"
                        )

    def _is_compatible_type(self, value: Any, expected_type: Any) -> bool:
        """Check if a value is compatible with expected type."""
        # This is a basic implementation - real type checking would be much more complex
        if expected_type in (int, float, str, bool, list, dict):
            return isinstance(value, expected_type)

        # Handle Union types, Optional, etc. - simplified
        if hasattr(expected_type, "__origin__"):
            if expected_type.__origin__ is Union:
                return any(self._is_compatible_type(value, arg) for arg in expected_type.__args__)

        # Handle object configurations
        if isinstance(value, ConfigurationObject) and "TYPE" in value:
            # Would need to check if the TYPE produces the expected type
            return True

        return True  # Default to True for complex cases

    def _import_object(self, object_path: str) -> Any:
        """Import an object from a module path."""
        if "." not in object_path:
            raise ImportError(f"Invalid object path: {object_path}")

        module_path, object_name = object_path.rsplit(".", 1)

        try:
            module = importlib.import_module(module_path)
            return getattr(module, object_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not import {object_path}: {e}")

    def _handle_sweep(self, parsed_args: argparse.Namespace) -> List[ConfigurationObject]:
        """Handle parameter sweeping."""
        sweep_configs = []

        if len(parsed_args.sweep) == 1 and "=" not in parsed_args.sweep[0]:
            # Complex sweep with function
            sweep_func_path = parsed_args.sweep[0]
            try:
                sweep_func = self._import_object(sweep_func_path)
                for overrides in sweep_func():
                    # Parse a configuration with these overrides
                    override_args = []
                    for key, value in overrides.items():
                        override_args.append(f"{key}={value}")

                    # Create new args with overrides
                    new_args = argparse.Namespace()
                    for attr, value in vars(parsed_args).items():
                        setattr(new_args, attr, value)
                    new_args.args = parsed_args.args + override_args

                    config = self._parse_single_config(new_args)
                    sweep_configs.append(config)

            except ImportError as e:
                raise ValueError(f"Could not import sweep function '{sweep_func_path}': {e}")

        else:
            # Simple sweep with key=val1,val2,... format
            sweep_params = []
            for sweep_arg in parsed_args.sweep:
                if "=" not in sweep_arg:
                    raise ValueError(f"Invalid sweep format: {sweep_arg}")

                key, values_str = sweep_arg.split("=", 1)
                values = [self._parse_value(v.strip()) for v in values_str.split(",")]
                sweep_params.append((key, values))

            # Generate all combinations
            import itertools

            for combination in itertools.product(*[values for _, values in sweep_params]):
                # Create override arguments
                override_args = []
                for (key, _), value in zip(sweep_params, combination):
                    override_args.append(f"{key}={value}")

                # Create new args with overrides
                new_args = argparse.Namespace()
                for attr, value in vars(parsed_args).items():
                    setattr(new_args, attr, value)
                new_args.args = parsed_args.args + override_args

                config = self._parse_single_config(new_args)
                sweep_configs.append(config)

        return sweep_configs

    def _show_object_help(self, object_path: str) -> None:
        """Show help for a specific object."""
        try:
            obj = self._import_object(object_path)
            self._print_object_help(obj, object_path)
        except ImportError as e:
            print(f"Error: Could not import {object_path}: {e}")

    def _print_object_help(self, obj: Any, path: str) -> None:
        """Print help information for an object."""
        print(f"For `{path}`:")

        try:
            if inspect.isclass(obj):
                signature = inspect.signature(obj.__init__)
            elif callable(obj):
                signature = inspect.signature(obj)
            else:
                print("  Not a callable object")
                return

            # Get docstring
            docstring = inspect.getdoc(obj)
            param_docs = {}
            if docstring:
                param_docs = self._parse_param_docs(docstring)

            # Print parameters
            for param_name, param in signature.parameters.items():
                if param_name in ("self", "cls"):
                    continue

                parts = [f"    {param_name}"]

                # Add type annotation
                if param.annotation != inspect.Parameter.empty:
                    parts.append(f"({param.annotation})")

                # Add default value
                if param.default != inspect.Parameter.empty:
                    parts.append(f"default={param.default!r}")

                # Add description
                if param_name in param_docs:
                    parts.append(f": {param_docs[param_name]}")

                print("".join(parts))

        except Exception as e:
            print(f"  Error inspecting object: {e}")

    def _parse_param_docs(self, docstring: str) -> Dict[str, str]:
        """Parse parameter documentation from docstring."""
        param_docs = {}

        # Simple parser for Google-style docstrings
        lines = docstring.split("\n")
        in_args_section = False

        for line in lines:
            line = line.strip()

            if line == "Args:" or line == "Arguments:":
                in_args_section = True
                continue

            if in_args_section:
                if line.startswith((" ", "\t")) and ":" in line:
                    # Parameter line
                    param_line = line.strip()
                    if ":" in param_line:
                        param_part, desc = param_line.split(":", 1)
                        param_name = param_part.strip().split("(")[0]  # Remove type info
                        param_docs[param_name] = desc.strip()
                elif line and not line.startswith((" ", "\t")):
                    # End of args section
                    in_args_section = False

        return param_docs

    def _print_and_confirm(self, config: ConfigurationObject) -> None:
        """Print configuration and wait for user confirmation."""
        print("Final Configuration:")
        print("=" * 50)

        pretty_config = config.pretty()
        for key, value in sorted(pretty_config.items()):
            print(f"{key}: {value!r}")

        print("=" * 50)
        input("Press Enter to continue...")
