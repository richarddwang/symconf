"""Configuration validation module."""

import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_args, get_origin

from .exceptions import MatchingError, TypeValidationError
from .parameter_tracer import ParameterChainTracer
from .utils import import_object

OBJECT_TYPE = Callable | Type[Any]


class ConfigValidator:
    """Configuration validator for type and parameter validation."""

    EMPTY_PARAM = inspect.Parameter.empty
    VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD

    def __init__(
        self,
        validate_type: bool = True,
        validate_mapping: bool = True,
        base_classes: Optional[Dict[str, type]] = None,
    ):
        """Initialize validator.

        Args:
            validate_type: Enable type validation
            validate_mapping: Enable parameter mapping validation
            base_classes: Base classes for validation context
        """
        self.validate_type = validate_type
        self.validate_mapping = validate_mapping
        self.base_classes = base_classes or {}
        self.parameter_tracer = ParameterChainTracer()

    def validate_recursive(self, config: Dict[str, Any], path: str = "") -> List[TypeValidationError | MatchingError]:
        """Recursively validate configuration.

        Args:
            config: Configuration to validate
            path: Current path for error reporting

        Returns:
            List of validation errors
        """
        errors = []
        if isinstance(config, dict):
            if "TYPE" in config and config["TYPE"] != "LIST":
                obj_errors = self.validate_object_config(config, path)
                errors.extend(obj_errors)
            else:
                for key, value in config.items():
                    nested_path = f"{path}.{key}" if path else key
                    nested_errors = self.validate_recursive(value, nested_path)
                    errors.extend(nested_errors)
        elif isinstance(config, list):
            for idx, item in enumerate(config):
                item_path = f"{path}[{idx}]"
                item_errors = self.validate_recursive(item, item_path)
                errors.extend(item_errors)
        return errors

    def validate_object_config(
        self, config: Dict[str, Any], path: str = ""
    ) -> List[TypeValidationError | MatchingError]:
        """Validate a single object configuration.

        Args:
            config: Object configuration with TYPE
            path: Current path for error reporting

        Returns:
            List of validation errors
        """
        errors = []
        try:
            obj = import_object(config["TYPE"])
        except Exception:
            # Skip validation if object cannot be imported
            return errors

        # Parse object once to get parameter information
        param_chain = self.get_parameter_chain(obj)

        if self.validate_mapping:
            mapping_errors = self._validate_parameter_mapping(config, obj, path, param_chain)
            errors.extend(mapping_errors)

        if self.validate_type:
            type_errors = self._validate_parameter_types(config, obj, path, param_chain)
            errors.extend(type_errors)

        return errors

    def get_parameter_chain(self, obj: OBJECT_TYPE) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get parameter chain through kwargs tracing.

        Args:
            obj: Object to trace parameter chain for

        Returns:
            Dict mapping object names to their parameter signatures
        """
        return self.parameter_tracer.trace_parameter_chain(obj)

    def _get_object_display_name(self, obj: OBJECT_TYPE) -> str:
        """Get display name for object.

        Args:
            obj: Object to get display name for

        Returns:
            Display name for error messages
        """
        return self.parameter_tracer._get_object_display_name(obj)

    def _validate_parameter_mapping(
        self,
        config: Dict[str, Any],
        obj: Any,
        path: str,
        param_chain: Dict[str, Dict[str, Dict[str, Any]]],
    ) -> List[MatchingError]:
        """Validate parameter mapping.

        Args:
            config: Object configuration
            obj: Object being configured
            path: Current path for error reporting
            param_chain: Parameter chain from parameter tracer

        Returns:
            List of parameter mapping errors
        """
        errors = []
        actual_params = set(config.keys()) - {"TYPE", "CLASS"}

        # Extract parameter information from param_chain
        all_expected_params = set()
        has_var_keyword = False
        required_params = set()

        # Collect parameters from all objects in the chain
        for obj_name, chain_signature in param_chain.items():
            for param_name, param_info in chain_signature.items():
                # Check if this signature has **kwargs
                if param_info["kind"] == inspect.Parameter.VAR_KEYWORD:
                    has_var_keyword = True
                    continue

                all_expected_params.add(param_name)

                # Only consider required if no **kwargs in this or any parent signature
                if param_info["default"] == inspect.Parameter.empty:
                    required_params.add(param_name)

        # Check for unexpected parameters (only if no **kwargs anywhere in chain)
        unexpected = actual_params - all_expected_params
        if unexpected and not has_var_keyword:
            param_list = []
            for param in sorted(unexpected):
                param_list.append(f"{path}.{param}" if path else param)

            errors.append(
                MatchingError(
                    error_type="Unexpected parameters",
                    parameters=param_list,
                    object_name=self._get_object_display_name(obj),
                )
            )

        # Check for missing required parameters
        missing = required_params - actual_params
        if missing:
            param_list = []
            for param in sorted(missing):
                param_list.append(f"{path}.{param}" if path else param)

            errors.append(
                MatchingError(
                    error_type="Missing parameters",
                    parameters=param_list,
                    object_name=self._get_object_display_name(obj),
                )
            )

        return errors

    def _validate_parameter_types(
        self, config: Dict[str, Any], obj: Any, path: str, param_chain: Dict[str, Dict[str, Dict[str, Any]]]
    ) -> List[TypeValidationError]:
        """Validate parameter types.

        Args:
            config: Object configuration
            obj: Object being configured
            path: Current path for error reporting
            param_chain: Parameter chain from parameter tracer

        Returns:
            List of type validation errors
        """
        errors = []
        all_param_types = {}
        for obj_name, chain_signature in param_chain.items():
            for param_name, param_info in chain_signature.items():
                if param_name not in all_param_types:
                    all_param_types[param_name] = param_info

        for param_name, value in config.items():
            if param_name in ["TYPE", "CLASS"]:
                continue

            if param_name in all_param_types:
                param_info = all_param_types[param_name]
                annotation = param_info["annotation"]

                if annotation != inspect.Parameter.empty:
                    param_path = f"{path}.{param_name}" if path else param_name
                    type_errors = self._validate_single_type(value, annotation, param_path)
                    errors.extend(type_errors)

            # Also validate nested objects if they have TYPE
            if isinstance(value, dict) and "TYPE" in value:
                nested_errors = self._validate_nested_object_type(value, param_name, path, all_param_types)
                errors.extend(nested_errors)

        return errors

    def _validate_nested_object_type(
        self, nested_config: Dict[str, Any], param_name: str, path: str, param_types: Dict[str, Dict[str, Any]]
    ) -> List[TypeValidationError]:
        """Validate that nested object type matches expected type.

        Args:
            nested_config: Nested object configuration
            param_name: Parameter name
            path: Current path
            param_types: Available parameter type info

        Returns:
            List of validation errors
        """
        errors = []
        if param_name in param_types:
            expected_type = param_types[param_name]["annotation"]
            param_path = f"{path}.{param_name}" if path else param_name

            try:
                actual_obj = import_object(nested_config["TYPE"])
                type_errors = self._validate_single_type(actual_obj, expected_type, param_path)
                errors.extend(type_errors)
            except Exception:
                # If we can't import the object, skip type validation
                pass

        return errors

    def _validate_single_type(self, value: Any, expected_type: type, param_path: str) -> List[TypeValidationError]:
        """Validate a single value against expected type.

        Args:
            value: Value to validate
            expected_type: Expected type
            param_path: Parameter path for error reporting

        Returns:
            List of validation errors
        """
        errors = []

        # Handle None values
        if value is None:
            if self._type_allows_none(expected_type):
                return errors
            else:
                errors.append(
                    TypeValidationError(
                        parameter=param_path,
                        expected=self._format_expected_type(expected_type),
                        actual_value=None,
                        actual_type="NoneType",
                    )
                )
                return errors

        # Handle Union types (including | syntax like SuperToy | None)
        origin = get_origin(expected_type)
        if origin is Union:
            args = get_args(expected_type)
            for arg in args:
                if arg is type(None) and value is None:
                    return errors  # None is allowed
                elif arg is not type(None) and self._value_matches_type(value, arg):
                    return errors  # Value matches one of the union types

            errors.append(
                TypeValidationError(
                    parameter=param_path,
                    expected=self._format_expected_type(expected_type),
                    actual_value=value,
                    actual_type=type(value).__name__,
                )
            )
            return errors

        # Handle Literal types
        if self._is_literal_type(expected_type):
            args = get_args(expected_type)
            if value not in args:
                errors.append(
                    TypeValidationError(
                        parameter=param_path,
                        expected=f"Literal{list(args)}",
                        actual_value=value,
                        actual_type=type(value).__name__,
                    )
                )
            return errors

        # Handle Type[X] (class type annotations)
        if self._is_type_annotation(expected_type):
            args = get_args(expected_type)
            if args:
                expected_class = args[0]
                if inspect.isclass(value):
                    if not issubclass(value, expected_class):
                        errors.append(
                            TypeValidationError(
                                parameter=param_path,
                                expected=f"Type[`{expected_class.__name__}`]",
                                actual_value=f"`{value.__name__}`",
                                actual_type=f"Type[{value.__name__}]",
                            )
                        )
                else:
                    errors.append(
                        TypeValidationError(
                            parameter=param_path,
                            expected=f"Type[`{expected_class.__name__}`]",
                            actual_value=f"`{value.__class__.__name__}`",
                            actual_type=f"{value.__class__.__name__}",
                        )
                    )
            return errors

        # Basic type checking
        if not self._value_matches_type(value, expected_type):
            errors.append(
                TypeValidationError(
                    parameter=param_path,
                    expected=self._format_expected_type(expected_type),
                    actual_value=value,
                    actual_type=type(value).__name__,
                )
            )

        return errors

    def _is_literal_type(self, type_annotation: Any) -> bool:
        """Check if type annotation is a Literal type.

        Args:
            type_annotation: Type annotation to check

        Returns:
            True if it's a Literal type
        """
        origin = get_origin(type_annotation)
        if hasattr(origin, "_name") and origin._name == "Literal":
            return True
        return str(type_annotation).startswith("typing.Literal")

    def _is_type_annotation(self, type_annotation: Any) -> bool:
        """Check if type annotation is Type[X].

        Args:
            type_annotation: Type annotation to check

        Returns:
            True if it's a Type[X] annotation
        """
        origin = get_origin(type_annotation)
        return origin is type

    def _type_allows_none(self, expected_type: type) -> bool:
        """Check if type allows None values.

        Args:
            expected_type: Type to check

        Returns:
            True if None is allowed
        """
        origin = get_origin(expected_type)
        if origin is Union:
            args = get_args(expected_type)
            return type(None) in args
        return False

    def _value_matches_type(self, value: Any, expected_type: type) -> bool:
        """Check if value matches expected type.

        Args:
            value: Value to check
            expected_type: Expected type

        Returns:
            True if value matches type
        """
        # Handle exact type matching first
        if type(value) is expected_type:
            return True

        # Strict type checking: int should NOT be accepted for float
        # This matches the HOWTO.md specification where percent: 1 is an error for float
        if expected_type is float:
            return isinstance(value, float) and not isinstance(value, bool)
        if expected_type is int:
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type is str:
            return isinstance(value, str)
        if expected_type is bool:
            return isinstance(value, bool)

        # Handle generic types
        origin = get_origin(expected_type)
        if origin:
            return isinstance(value, origin)

        # Handle class instances and inheritance
        if inspect.isclass(expected_type):
            return isinstance(value, expected_type)

        # Default fallback for other types
        return isinstance(value, expected_type)

    def _format_expected_type(self, expected_type: type) -> str:
        """Format expected type for error messages.

        Args:
            expected_type: Type to format

        Returns:
            Formatted type string
        """
        if expected_type in (int, float, str, bool):
            return expected_type.__name__

        if hasattr(expected_type, "__name__"):
            return expected_type.__name__

        return str(expected_type)
