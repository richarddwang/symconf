"""SynConf parser module."""

import argparse
import inspect
import sys
from copy import copy
from itertools import product
from typing import Any, Dict, List, Optional, Union

import yaml
from dotenv import load_dotenv

from .config import SynConfig
from .exceptions import ParameterValidationError
from .interpolation import InterpolationEngine
from .parameter_tracer import ParameterChainTracer
from .utils import (
    deep_merge,
    import_object,
    load_yaml,
    process_list_type,
    remove_parameters,
)
from .validation import ConfigValidator


class SynConfParser:
    """Main SynConf parser class."""

    def __init__(
        self,
        validate_type: bool = True,
        validate_mapping: bool = True,
        base_classes: Optional[Dict[str, type]] = None,
        validate_exclude: Optional[List[str]] = None,
    ):
        """Initialize SynConf parser.

        Args:
            validate_type: Enable type validation
            validate_mapping: Enable parameter mapping validation
            base_classes: Base classes for validation context
            validate_exclude: Parameter paths to exclude from validation
        """
        self.validate_type = validate_type
        self.validate_mapping = validate_mapping
        self.base_classes = base_classes or {}
        self.validate_exclude = validate_exclude or []

    def parse_args(self, args: Optional[List[str]] = None) -> Union[SynConfig, List[SynConfig]]:
        """Parse arguments and return configuration.

        Args:
            args: Command line arguments (defaults to sys.argv[1:])

        Returns:
            Single configuration or list of configurations (if sweeping)
        """
        if args is None:
            args = sys.argv[1:]

        # Parse command line arguments
        parsed_args = self._parse_command_line(args)

        # Handle help commands
        if parsed_args.help_object:
            self._show_object_help(parsed_args.help_object)
            sys.exit(0)

        # Handle sweeping
        if parsed_args.sweep_params or parsed_args.sweep_fn:
            return self._handle_sweeping(parsed_args)

        # Regular single configuration parsing
        config = self._build_single_config(parsed_args)

        # Show configuration if requested
        if parsed_args.print_config:
            self._print_config(config)
            input("Press Enter to continue...")

        return config

    def _parse_command_line(self, args: List[str]) -> argparse.Namespace:
        """Parse command line arguments.

        Args:
            args: Command line arguments

        Returns:
            Parsed arguments namespace
        """
        parser = argparse.ArgumentParser(description="SynConf Configuration Parser")

        # Positional arguments for YAML files
        parser.add_argument("config_files", nargs="*", help="YAML configuration files")

        # Optional arguments
        parser.add_argument("--env", action="append", help="Dotenv file path")
        parser.add_argument("--args", nargs="*", help="Parameter overrides (key=value)")
        parser.add_argument("--print", dest="print_config", action="store_true", help="Print final configuration")
        parser.add_argument("--help.object", dest="help_object", help="Show object parameter help")
        parser.add_argument("--sweep_fn", help="Custom sweep generator function")

        # Parse known args to handle --sweep.* arguments
        known_args, remaining = parser.parse_known_args(args)

        # Parse sweep parameters
        sweep_params = {}
        i = 0
        while i < len(remaining):
            arg = remaining[i]
            if arg.startswith("--sweep."):
                param_name = arg[8:]  # Remove '--sweep.' prefix
                values = []
                i += 1
                while i < len(remaining) and not remaining[i].startswith("--"):
                    # Collect space-separated values
                    values.append(remaining[i])
                    i += 1
                sweep_params[param_name] = values
            else:
                i += 1

        known_args.sweep_params = sweep_params
        return known_args

    def _build_single_config(self, args: argparse.Namespace) -> SynConfig:
        """Build a single configuration from arguments.

        Args:
            args: Parsed command line arguments  # (namespace with config options)

        Returns:
            Built configuration  # (validated and processed SynConfig)
        """
        # Step 1: Load YAML files and merge them
        config = {}  # Dict[str, Any] (merged configuration)
        for config_file in args.config_files:
            with open(config_file, "r") as f:
                file_config = load_yaml(f)
                assert isinstance(file_config, dict), (
                    f"Config file {config_file} must contain a YAML mapping at the top level."
                )
                # Deep merge configurations to handle nested structures
                config = deep_merge(config, file_config)

        # Load environment variables and update global environment
        dotenv_files = args.env or []
        for dotenv_file in dotenv_files:
            assert load_dotenv(dotenv_file), f"Failed to load dotenv file: {dotenv_file}"

        # Step 2: Apply command line overrides
        if args.args:
            yaml_content = "\n".join(arg.replace("=", ": ") for arg in args.args)
            args_config = load_yaml(yaml_content)
            for key, value in args_config.items():
                self._set_nested_value(config, key, value)

        # Step 3: Remove parameters marked as REMOVE
        config = remove_parameters(config)

        # Step 4: Complete default values for objects with TYPE
        config = self._complete_default_values(config)

        # Step 5: Resolve interpolations (variable references)
        config = InterpolationEngine(config).resolve_all_interpolations()

        # Step 6: Process LIST types (convert LIST markers to actual lists)
        config = process_list_type(config)

        # Step 7: Validate configuration against object signatures
        if self.validate_type or self.validate_mapping:
            self._validate_configuration(config)

        return SynConfig(config)

    def _set_nested_value(self, config: Dict[str, Any], key_path: str, value: Any) -> None:
        """Set nested value using dot notation.

        Args:
            config: Configuration dictionary
            key_path: Dot-separated key path
            value: Value to set
        """
        keys = key_path.split(".")
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _complete_default_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Complete default values for objects with TYPE.

        Args:
            config: Configuration data

        Returns:
            Configuration with completed default values
        """
        result = {}

        if "TYPE" in config:
            # This is an object definition, complete its defaults
            result = self._complete_object_defaults(config)
        else:
            result = copy(config)

        # Recursively process nested dictionaries
        for key, value in list(result.items()):
            if isinstance(value, dict):
                result[key] = self._complete_default_values(value)

        return result

    def _complete_object_defaults(self, obj_config: Dict[str, Any]) -> Dict[str, Any]:
        """Complete default values for a single object.

        Args:
            obj_config: Object configuration with TYPE

        Returns:
            Object configuration with defaults completed
        """
        # Skip LIST types as they are special keywords, not importable objects
        if obj_config["TYPE"] == "LIST":
            return obj_config

        obj = import_object(obj_config["TYPE"])

        # Get the full parameter chain through **kwargs tracing
        param_chain = ParameterChainTracer().trace_parameter_chain(obj)

        # Complete defaults from all objects in the chain
        result = obj_config
        for obj_type, signature in param_chain.items():
            for param_name, param_info in signature.items():
                if param_name not in result and param_info["default"] != inspect.Parameter.empty:
                    result[param_name] = param_info["default"]

        return result

    def _validate_configuration(self, config: Dict[str, Any]) -> None:
        """Validate configuration against object definitions.

        Args:
            config: Configuration to validate

        Raises:
            ParameterValidationError: If validation fails
        """
        validator = ConfigValidator(
            validate_type=self.validate_type,
            validate_mapping=self.validate_mapping,
            base_classes=self.base_classes,
            validate_exclude=self.validate_exclude,
        )

        errors = validator.validate_recursive(config)
        if errors:
            raise ParameterValidationError(errors)

    def _handle_sweeping(self, args: argparse.Namespace) -> List[SynConfig]:
        """Handle parameter sweeping.

        Args:
            args: Parsed arguments with sweep parameters

        Returns:
            List of configurations for different parameter combinations
        """
        if args.sweep_fn:
            return self._handle_custom_sweeping(args)
        else:
            return self._handle_simple_sweeping(args)

    def _handle_simple_sweeping(self, args: argparse.Namespace) -> List[SynConfig]:
        """Handle simple parameter sweeping.

        Args:
            args: Parsed arguments with sweep parameters

        Returns:
            List of configurations
        """
        base_config_args = argparse.Namespace(**vars(args))
        base_config_args.sweep_params = {}
        base_config_args.sweep_fn = None

        # Generate all parameter combinations
        param_names = list(args.sweep_params.keys())
        param_values = list(args.sweep_params.values())

        configs = []
        for combination in product(*param_values):
            # Create modified args for this combination
            modified_args = argparse.Namespace(**vars(base_config_args))
            additional_args = []
            for param_name, value in zip(param_names, combination):
                additional_args.append(f"{param_name}={value}")

            # Handle case where original args is None (no --args provided)
            existing_args = modified_args.args if modified_args.args is not None else []
            modified_args.args = list(existing_args) + additional_args
            config = self._build_single_config(modified_args)
            configs.append(config)

        return configs

    def _handle_custom_sweeping(self, args: argparse.Namespace) -> List[SynConfig]:
        """Handle custom parameter sweeping.

        Args:
            args: Parsed arguments with custom sweep function

        Returns:
            List of configurations
        """
        # Import the custom generator function
        generator_func = import_object(args.sweep_fn)

        base_config_args = argparse.Namespace(**vars(args))
        base_config_args.sweep_params = {}
        base_config_args.sweep_fn = None

        configs = []
        for param_overrides in generator_func():
            # Create modified args for this override set
            modified_args = argparse.Namespace(**vars(base_config_args))
            additional_args = []
            for param_name, value in param_overrides.items():
                additional_args.append(f"{param_name}={value}")

            existing_args = modified_args.args if modified_args.args is not None else []
            modified_args.args = list(existing_args) + additional_args
            config = self._build_single_config(modified_args)
            configs.append(config)

        return configs

    def _print_config(self, config: SynConfig) -> None:
        """Print configuration in YAML format.

        Args:
            config: Configuration to print
        """
        print("Final Configuration:")
        print("=" * 50)
        print(yaml.dump(config._to_dict(), default_flow_style=False, indent=2))

    def _show_object_help(self, object_path: str) -> None:
        """Show help for an object's parameters.

        Args:
            object_path: Path to the object
        """
        obj = import_object(object_path)
        tracer = ParameterChainTracer()

        # Get formatted help display using the parameter tracer
        help_output = tracer.format_help_display(obj)
        print(help_output)
