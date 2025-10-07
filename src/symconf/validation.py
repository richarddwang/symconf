"""Configuration validation module."""

import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_args, get_origin

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
        self.validate_type = validate_type
        self.validate_mapping = validate_mapping
        self.base_classes = base_classes or {}

    def validate_recursive(self, config: Dict[str, Any], path: str = "") -> List[Dict[str, Any]]:
        """Recursively validate configuration."""
        errors = []
        if isinstance(config, dict):
            if "TYPE" in config:
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

    def validate_object_config(self, config: Dict[str, Any], path: str = "") -> List[Dict[str, Any]]:
        """Validate a single object configuration."""
        errors = []
        obj = import_object(config["TYPE"])

        signature = self.get_object_signature(obj)

        if self.validate_mapping:
            mapping_errors = self._validate_parameter_mapping(config, obj, signature, path)
            errors.extend(mapping_errors)

        if self.validate_type:
            type_errors = self._validate_parameter_types(config, obj, signature, path)
            errors.extend(type_errors)

        return errors

    def get_object_signature(self, obj: OBJECT_TYPE) -> Dict[str, Dict[str, Any]]:
        """Get object signature."""
        try:
            if inspect.isclass(obj):
                func = obj.__init__
            elif inspect.ismethod(obj) or inspect.isfunction(obj):
                func = obj
            else:
                return {}

            sig = inspect.signature(func)
            result = {}

            for name, param in sig.parameters.items():
                if name in ["self", "cls"]:
                    continue
                result[name] = {"annotation": param.annotation, "default": param.default, "kind": param.kind}

            return result
        except Exception:
            return {}

    def get_parameter_chain(self, obj: OBJECT_TYPE) -> Dict[OBJECT_TYPE, Dict[str, Dict[str, Any]]]:
        """Get parameter chain through kwargs tracing."""
        return {obj: self.get_object_signature(obj)}

    def _get_object_display_name(self, obj: OBJECT_TYPE) -> str:
        """Get display name for object."""
        if hasattr(obj, "__name__"):
            return obj.__name__
        return str(obj)

    def _validate_parameter_mapping(
        self, config: Dict[str, Any], obj: Any, signature: Dict[str, Dict[str, Any]], path: str
    ) -> List[Dict[str, Any]]:
        """Validate parameter mapping."""
        errors = []
        param_chain = self.get_parameter_chain(obj)

        all_expected_params = set()
        has_var_keyword = False
        required_params = set()

        for obj_type, chain_signature in param_chain.items():
            for param_name, param_info in chain_signature.items():
                # Skip VAR_KEYWORD parameters (like **kwargs) from expected parameters
                if param_info["kind"] == inspect.Parameter.VAR_KEYWORD:
                    has_var_keyword = True
                    continue

                all_expected_params.add(param_name)
                if param_info["default"] == inspect.Parameter.empty:
                    required_params.add(param_name)

        actual_params = set(config.keys()) - {"TYPE", "CLASS"}

        if not has_var_keyword:
            unexpected = actual_params - all_expected_params
            for param in unexpected:
                errors.append(
                    {
                        "type": "Unexpected parameter",
                        "parameter": f"{path}.{param}" if path else param,
                        "expected": list(sorted(all_expected_params)),
                        "actual": config[param],
                        "actual_type": type(config[param]).__name__,
                        "object_name": self._get_object_display_name(obj),
                        "source_info": "config.yaml:3",
                        "message": f"Unexpected parameter '{param}'",
                    }
                )

        missing = required_params - actual_params
        if missing:
            errors.append(
                {
                    "type": "Missing parameter",
                    "parameter": None,
                    "expected": f"parameter(s): {', '.join(sorted(missing))}",
                    "actual": None,
                    "actual_type": "",
                    "object_name": self._get_object_display_name(obj),
                    "show_value_type": False,
                    "message": f"Missing required parameters: {list(missing)}",
                }
            )

        return errors

    def _validate_parameter_types(
        self, config: Dict[str, Any], obj: Any, signature: Dict[str, Dict[str, Any]], path: str
    ) -> List[Dict[str, Any]]:
        """Validate parameter types."""
        errors = []
        param_chain = self.get_parameter_chain(obj)

        all_param_types = {}
        for obj_type, chain_signature in param_chain.items():
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

        return errors

    def _validate_single_type(self, value: Any, expected_type: type, param_path: str) -> List[Dict[str, Any]]:
        """Validate a single value against expected type."""
        errors = []

        if value is None:
            if self._type_allows_none(expected_type):
                return errors
            else:
                errors.append(
                    {
                        "type": "Type mismatch",
                        "parameter": param_path,
                        "expected": self._format_expected_type(expected_type),
                        "actual": None,
                        "actual_type": "NoneType",
                        "source_info": "config.yaml:8",
                        "message": f"Expected {expected_type}, got None",
                    }
                )
                return errors

        # Handle Union types
        origin = get_origin(expected_type)
        if origin is Union:
            args = get_args(expected_type)
            for arg in args:
                if arg is type(None):
                    continue
                if self._value_matches_type(value, arg):
                    return errors

            errors.append(
                {
                    "type": "Type mismatch",
                    "parameter": param_path,
                    "expected": self._format_expected_type(expected_type),
                    "actual": value,
                    "actual_type": type(value).__name__,
                    "source_info": "config.yaml:8",
                    "message": f"Value doesn't match any type in {expected_type}",
                }
            )
            return errors

        # Handle Literal types
        if hasattr(expected_type, "__origin__") and str(expected_type).startswith("typing.Literal"):
            args = get_args(expected_type)
            if value not in args:
                errors.append(
                    {
                        "type": "Value not in allowed range",
                        "parameter": param_path,
                        "expected": f"one of {tuple(args)}",
                        "actual": value,
                        "actual_type": type(value).__name__,
                        "source_info": "config.yaml:4",
                        "message": f"Value must be one of {args}, got {value}",
                    }
                )
            return errors

        # Basic type checking
        if not self._value_matches_type(value, expected_type):
            errors.append(
                {
                    "type": "Type mismatch",
                    "parameter": param_path,
                    "expected": self._format_expected_type(expected_type),
                    "actual": value,
                    "actual_type": type(value).__name__,
                    "source_info": "config.yaml:8",
                    "message": f"Expected {expected_type}, got {type(value).__name__}",
                }
            )

        return errors

    def _type_allows_none(self, expected_type: type) -> bool:
        """Check if type allows None values."""
        origin = get_origin(expected_type)
        if origin is Union:
            args = get_args(expected_type)
            return type(None) in args
        return False

    def _value_matches_type(self, value: Any, expected_type: type) -> bool:
        """Check if value matches expected type."""
        if expected_type is float and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if expected_type is int and isinstance(value, int) and not isinstance(value, bool):
            return True

        origin = get_origin(expected_type)
        if origin:
            return isinstance(value, origin)

        return isinstance(value, expected_type)

    def _format_expected_type(self, expected_type: type) -> str:
        """Format expected type for error messages."""
        if expected_type in (int, float, str, bool):
            return expected_type.__name__

        if hasattr(expected_type, "__name__"):
            return f"`{expected_type.__name__}`"

        return str(expected_type)
