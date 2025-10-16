"""SynConf parser module."""

import argparse
import inspect
import sys
from copy import copy
from itertools import product
from typing import Any, Dict, List, Optional, Union

import yaml

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
        if parsed_args.sweep:
            return self._handle_sweeping(parsed_args.sweep, parsed_args.configs)

        # Regular single configuration parsing
        config = self._build_config(parsed_args)

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
        parser.add_argument(
            "configs",
            nargs="*",
            help="YAML configuration file or parameter overwrites in format <key path>=<value in yaml>.",
        )
        parser.add_argument("--print", dest="print_config", action="store_true", help="Print final configuration")
        parser.add_argument("--help.object", dest="help_object", help="Show object parameter help")
        parser.add_argument("--sweep", nargs="*", help="Custom sweep generator function")
        args = parser.parse_args(args)
        return args

    def _build_config(self, args: argparse.Namespace) -> SynConfig:
        """Build a single configuration from arguments.

        Args:
            args: Parsed command line arguments  # (namespace with config options)

        Returns:
            Built configuration  # (validated and processed SynConfig)
        """
        config = {}  # Dict[str, Any]

        # Step 1: Load YAML files and paramter overwrites in order
        for config_file_or_overwrite in args.configs:
            if config_file_or_overwrite.endswith((".yaml", ".yml")):
                # Load configuration file
                config_file = config_file_or_overwrite
                with open(config_file, "r") as f:
                    file_config = load_yaml(f)
                    assert isinstance(file_config, dict), (
                        f"Config file {config_file} must contain a YAML mapping at the top level."
                    )
                    # Deep merge configurations to handle nested structures
                    config = deep_merge(config, file_config)
            else:
                # Handle parameter overwrite
                config_overwrite = config_file_or_overwrite
                key, value_str = config_overwrite.split("=", 1)
                self._set_nested_value(config, key, load_yaml(value_str))

        # Step 2: Remove parameters marked as REMOVE
        config = remove_parameters(config)

        # Step 3: Complete default values for objects with TYPE
        config = self._complete_default_values(config)

        # Step 4: Resolve interpolations (variable references)
        config = InterpolationEngine(config).resolve_all_interpolations()

        # Step 5: Process LIST types (convert LIST markers to actual lists)
        config = process_list_type(config)

        # Step 6: Validate configuration against object signatures
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

    def _handle_sweeping(self, sweep_args: List[str], config_args: list[str]) -> List[SynConfig]:
        """Handle parameter sweeping.

        Args:
            sweep_args: Arguments of --sweep
            config_args: Arguments for original basic configuration files and overrides
        Returns:
            List of configurations for different parameter combinations
        """
        # Get generator generates list of <key>=<value> pairs (list[str])
        if len(sweep_args) > 0 and "=" not in sweep_args[0]:
            # Complex sweeping: through customized generator function. e.g., --sweep my_module.my_function
            generator_fn = import_object(sweep_args[0])
            pair_strs_generator = generator_fn()
        else:
            # Simple sweeping: through multiple key-values pairs. e.g., --sweep key1=[v1,v2] key2=[v3,v4]
            nested_pairs: list[list[str]] = []  # (#parameters, #possible values)
            for sweep_arg in sweep_args:
                key, values_str = sweep_arg.split("=", 1)
                value_strs = values_str.replace("[", "").replace("]", "").replace(" ", "").split(",")
                pair_strs = [f"{key}={v}" for v in value_strs]
                nested_pairs.append(pair_strs)
            pair_strs_generator = product(*nested_pairs)

        # Build configurations for all combinations
        configs = []
        for pair_strs in pair_strs_generator:
            # Create modified args for this combination
            extended_args = config_args + list(pair_strs)

            # Build configuration for this combination
            config = self.parse_args(extended_args)
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
