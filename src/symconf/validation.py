"""Configuration validation module."""

import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_args, get_origin

from .exceptions import MatchingError, TypeValidationError
from .parameter_tracer import ParameterChainTracer
from .utils import get_method_class, import_object

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
        # Parse object to get parameter information
        obj = import_object(config["TYPE"])
        params = self.parameter_tracer.get_all_parameters(obj)

        # Collect validation errors
        errors = []

        if self.validate_mapping:
            mapping_errors = self._validate_parameter_mapping(config, obj, path, params)
            errors.extend(mapping_errors)

        if self.validate_type:
            type_errors = self._validate_parameter_types(config, obj, path, params)
            errors.extend(type_errors)

        return errors

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
        params: Dict[str, Dict[str, Any]],
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

        # Actual parameters provided in config (excluding special keys)
        actual_params = set(config.keys()) - {"TYPE", "CLASS"}

        # Extract parameter information from param_chain
        all_expected_params = set()
        has_var_keyword = False
        required_params = set()

        # Collect parameters from all objects in the chain
        for param_name, param_info in params.items():
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
        self, config: Dict[str, Any], obj: Any, path: str, params: dict[str, Dict[str, Any]]
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

        for key, value in config.items():
            nested_path = f"{path}.{key}" if path else key

            if key == "TYPE" or key not in params:
                continue
            elif key == "CLASS":
                class_obj = import_object(value["TYPE"])
                method_class = get_method_class(obj)
                if not issubclass(class_obj, method_class):
                    errors.append(
                        TypeValidationError(
                            parameter=nested_path,
                            expected_type=method_class,
                            actual_value=value["TYPE"],
                            actual_type=class_obj,
                        )
                    )
            else:
                errors.extend(
                    self._validate_single_value(
                        value,
                        expected_type=params[key]["annotation"],
                        param_path=nested_path,
                    )
                )

        return errors

    def _validate_single_value(self, value: Any, expected_type: type, param_path: str) -> List[TypeValidationError]:
        """Validate a single value against expected type.

        Args:
            value: Value to validate
            expected_type: Expected type
            param_path: Parameter path for error reporting

        Returns:
            List of validation errors
        """
        errors = []

        # Identify actual type
        if isinstance(value, dict) and "TYPE" in value:
            actual_type = import_object(value["TYPE"])
        else:
            actual_type = type(value)

        # Handle Union types (including `|`, `Optional`)
        origin = get_origin(expected_type)
        if origin is Union:
            args = get_args(expected_type)
            for arg in args:
                if issubclass(actual_type, arg):
                    return errors

            errors.append(
                TypeValidationError(
                    parameter=param_path,
                    expected_type=expected_type,
                    actual_value=value,
                    actual_type=actual_type,
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
                        expected_type=expected_type,
                        actual_value=value,
                        actual_type=actual_type,
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
                                expected_type=expected_type,
                                actual_value=value,
                                actual_type=actual_type,
                            )
                        )
                else:
                    errors.append(
                        TypeValidationError(
                            parameter=param_path,
                            expected_type=expected_type,
                            actual_value=value,
                            actual_type=actual_type,
                        )
                    )
            return errors

        # Basic type checking
        if origin:  # Generic types like List[X], Dict[X, Y], etc. we only check the outer type
            expected_type = origin
        if not issubclass(actual_type, expected_type):
            errors.append(
                TypeValidationError(
                    parameter=param_path,
                    expected_type=expected_type,
                    actual_value=value,
                    actual_type=actual_type,
                )
            )
            return errors

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
