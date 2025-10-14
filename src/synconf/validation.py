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
        validate_exclude: Optional[List[str]] = None,
    ):
        """Initialize validator.

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
            config: Object configuration  # (config dict with parameters)
            obj: Object being configured
            path: Current path for error reporting  # (dot-separated path)
            params: Parameter chain from parameter tracer  # (param name -> param info)

        Returns:
            List of parameter mapping errors  # (list of validation errors)
        """
        errors = []  # List[MatchingError] (validation errors)

        # Actual parameters provided in config (excluding special keys)
        actual_params = set(config.keys()) - {"TYPE"}  # Set[str] (provided parameters)

        # Extract parameter information from param_chain
        all_expected_params = set()  # Set[str] (all acceptable parameters)
        required_params = set()  # Set[str] (parameters without defaults)
        has_kwargs = False

        # Collect parameters from all objects in the chain
        for param_name, param_info in params.items():
            # Skip **kwargs parameters
            if param_info["kind"] == inspect.Parameter.VAR_KEYWORD:
                has_kwargs = True
                continue

            all_expected_params.add(param_name)

            # Consider required if no default value
            if param_info["default"] == inspect.Parameter.empty:
                required_params.add(param_name)

        # Check for unexpected parameters
        if not has_kwargs:
            unexpected = actual_params - all_expected_params - set(self.validate_exclude)  # Set[str] (extra parameters)
            if unexpected:
                param_list = []  # List[str] (formatted parameter paths)
                for param in sorted(unexpected):
                    param_path = f"{path}.{param}" if path else param
                    if param_path not in self.validate_exclude:
                        param_list.append(param_path)

                if param_list:
                    errors.append(
                        MatchingError(
                            error_type="Unexpected parameters",
                            parameters=param_list,
                            object_name=self._get_object_display_name(obj),
                        )
                    )

        # Check for missing required parameters
        missing = required_params - actual_params  # Set[str] (missing required parameters)
        if missing:
            param_list = []  # List[str] (formatted parameter paths)
            for param in sorted(missing):
                param_path = f"{path}.{param}" if path else param
                if param_path not in self.validate_exclude:
                    param_list.append(param_path)

            if param_list:
                errors.append(
                    MatchingError(
                        error_type="Missing parameters",
                        parameters=param_list,
                        object_name=self._get_object_display_name(obj),
                    )
                )

        return errors

    def _validate_parameter_types(
        self, config: Dict[str, Any], obj: Any, path: str, params: Dict[str, Dict[str, Any]]
    ) -> List[TypeValidationError]:
        """Validate parameter types.

        Args:
            config: Object configuration  # (config dict with typed parameters)
            obj: Object being configured
            path: Current path for error reporting  # (dot-separated path)
            params: Parameter chain from parameter tracer  # (param name -> param info)

        Returns:
            List of type validation errors  # (list of type mismatches)
        """
        errors = []  # List[TypeValidationError] (type validation errors)

        # Check each configured parameter
        for i, (key, value) in enumerate(config.items()):
            nested_path = f"{path}.{key}" if path else key

            # Skip special keys, excluded parameters, and unknown parameters
            if key == "TYPE" or nested_path in self.validate_exclude or key not in params:
                continue
            # Handle self parameter for instance methods
            elif i == 0 and key == "self":
                class_type: str = config["TYPE"].rsplit(".", 1)[0]
                expected_type = import_object(class_type)
                errors.extend(
                    self._validate_single_value(
                        value,
                        expected_type=expected_type,
                        param_path=nested_path,
                    )
                )
            else:
                # Only validate if parameter has type annotation
                expected_type = params[key]["annotation"]
                if expected_type != inspect.Parameter.empty:
                    errors.extend(
                        self._validate_single_value(
                            value,
                            expected_type=expected_type,
                            param_path=nested_path,
                        )
                    )

        return errors

    def _matches_type(self, value: Any, actual_type: type, expected_type: type) -> bool:
        """Check if a value matches an expected type.

        Args:
            value: Value to check
            actual_type: Actual type of the value
            expected_type: Expected type to match against

        Returns:
            True if value matches expected type
        """
        # Handle ForwardRef types
        if hasattr(expected_type, "__forward_arg__"):
            # Skip ForwardRef validation for now - would need runtime resolution.
            # First import module of object owns this parameter and then get forward arg from that module.
            return True

        # Handle Literal types
        if self._is_literal_type(expected_type):
            literal_args = get_args(expected_type)
            return value in literal_args

        # Handle Type[X] (class type annotations)
        if self._is_type_annotation(expected_type):
            args = get_args(expected_type)
            if args:
                expected_class = args[0]
                if inspect.isclass(value):
                    return issubclass(value, expected_class)
                else:
                    return False
            return False

        # Handle regular class types
        if inspect.isclass(expected_type):
            try:
                return issubclass(actual_type, expected_type)
            except TypeError:
                # Handle non-class types
                return actual_type == expected_type

        # Handle container types like list[float] - check outer type only
        expected_origin = get_origin(expected_type)
        if expected_origin is not None:
            return issubclass(actual_type, expected_origin)

        # Fallback to direct type comparison
        return issubclass(actual_type, expected_type)

    def _validate_single_value(self, value: Any, expected_type: type, param_path: str) -> List[TypeValidationError]:
        """Validate a single value against expected type.

        Args:
            value: Value to validate  # (parameter value to check)
            expected_type: Expected type  # (type annotation from signature)
            param_path: Parameter path for error reporting  # (dot-separated path)

        Returns:
            List of validation errors  # (list of type mismatches)
        """
        errors = []  # List[TypeValidationError] (type validation errors)

        # Identify actual type based on value
        if isinstance(value, dict) and "TYPE" in value:
            # Handle object configurations with TYPE
            obj = import_object(value["TYPE"])
            # For functions, use the return type annotation
            if inspect.isfunction(obj) or inspect.ismethod(obj):
                sig = inspect.signature(obj)
                if sig.return_annotation != inspect.Signature.empty:
                    actual_type = sig.return_annotation
                else:
                    # No return type annotation, can't validate
                    return errors
            else:
                actual_type = obj
        else:
            # Regular value, use its type
            actual_type = type(value)

        # Handle Union types (including `|`, `Optional`)
        origin = get_origin(expected_type)
        # Handle both typing.Union and new | syntax (types.UnionType in Python 3.10+)
        is_union_type = (origin is Union) or (
            hasattr(expected_type, "__class__") and expected_type.__class__.__name__ == "UnionType"
        )
        if is_union_type:
            args = get_args(expected_type)  # Tuple[Type, ...] (union member types)

            # Check if value matches any union member using consolidated logic
            for arg in args:
                if self._matches_type(value, actual_type, arg):
                    return errors

            # No union member matched
            errors.append(
                TypeValidationError(
                    parameter=param_path,
                    expected_type=expected_type,
                    actual_value=value,
                    actual_type=actual_type,
                )
            )
            return errors

        # Use consolidated type matching for non-Union types
        if not self._matches_type(value, actual_type, expected_type):
            errors.append(
                TypeValidationError(
                    parameter=param_path,
                    expected_type=expected_type,
                    actual_value=value,
                    actual_type=actual_type,
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

    def get_parameter_chain(self, obj: OBJECT_TYPE) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get parameter chain for an object.

        Args:
            obj: Object to get parameter chain for

        Returns:
            Parameter chain dictionary  # (nested dict with parameter chain info)
        """
        return self.parameter_tracer.trace_parameter_chain(obj)

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
