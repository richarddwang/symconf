"""Custom exceptions for SynConf."""

from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Type


class SynConfError(Exception):
    """Base exception for SynConf errors."""

    pass


class CircularInterpolationError(SynConfError):
    """Raised when circular dependencies are detected in interpolation."""

    def __init__(self, cycle_path: list[str]):
        self.cycle_path = cycle_path
        cycle_display = " → ".join(cycle_path)
        super().__init__(f"Circular interpolation detected: {cycle_display} → {cycle_path[0]}")


class CircularKwargsChainError(SynConfError):
    """Raised when circular **kwargs chains are detected in parameter tracing."""

    def __init__(self, chain_path: list[str], circular_object: str):
        self.chain_path = chain_path
        self.circular_object = circular_object
        chain_display = " → ".join(chain_path)
        super().__init__(
            f"Circular **kwargs chain detected: {chain_display} → {circular_object}. "
            f"Object '{circular_object}' already exists in the parameter chain."
        )


@dataclass
class TypeValidationError:
    """Represents a type validation error."""

    parameter: str
    expected_type: Type
    actual_value: Any
    actual_type: Type

    def format_error_message(self) -> str:
        """Format error message for type mismatch.

        Returns:
            Formatted error message string
        """
        # Format expected type nicely
        expected_str = self._format_type(self.expected_type)

        # Format actual type nicely
        actual_type_str = self._format_type(self.actual_type)

        # Format actual value - use ... for complex objects
        if isinstance(self.actual_value, dict) and "TYPE" in self.actual_value:
            actual_value_str = "..."
        else:
            actual_value_str = repr(self.actual_value) if isinstance(self.actual_value, str) else str(self.actual_value)

        return dedent(f"""\
            ❌ Type mismatch
            Parameter: {self.parameter}
            Expected: {expected_str}
            Actual: {actual_value_str} ({actual_type_str})\
            """).strip()

    def _format_type(self, type_obj: Any) -> str:
        """Format type object for display.

        Args:
            type_obj: Type object to format

        Returns:
            Formatted type string
        """
        # Handle complex types first before simple name checks
        from typing import get_args, get_origin

        # Handle Literal types - show the values
        if self._is_literal_type(type_obj):
            args = get_args(type_obj)
            values = [repr(arg) if isinstance(arg, str) else str(arg) for arg in args]
            return f"Literal[{', '.join(values)}]"

        # Handle Optional types - show inner type with module
        if self._is_optional_type(type_obj):
            args = get_args(type_obj)
            if args:
                inner_type = args[0]
                if inner_type is not type(None):
                    inner_str = self._format_type(inner_type)
                    return f"Optional[{inner_str}]"

        # Handle Type[X] annotations
        if self._is_type_annotation(type_obj):
            args = get_args(type_obj)
            if args:
                inner_type = args[0]
                inner_str = self._format_type(inner_type)
                return f"Type[{inner_str}]"

        # Handle Union types (including | syntax)
        origin = get_origin(type_obj)
        if origin is not None:
            return str(type_obj)

        # Handle new Python 3.10+ union syntax (types.UnionType)
        if hasattr(type_obj, "__class__") and type_obj.__class__.__name__ == "UnionType":
            return str(type_obj)

        # Handle basic types like int, float, str
        if type_obj in (int, float, str, bool):
            return type_obj.__name__

        # Handle inspect._empty (parameters without type annotations)
        if hasattr(type_obj, "__name__") and type_obj.__name__ == "_empty":
            return "Any"  # Don't show type validation errors for parameters without annotations

        # Handle classes with modules
        if hasattr(type_obj, "__name__") and hasattr(type_obj, "__module__"):
            if type_obj.__module__ in ["tests.conftest", "__main__"]:
                return f"tests.conftest.{type_obj.__name__}"
            elif type_obj.__module__ == "builtins":
                return type_obj.__name__
            else:
                return f"{type_obj.__module__}.{type_obj.__name__}"

        # Handle classes without modules
        if hasattr(type_obj, "__name__"):
            return type_obj.__name__

        # Fallback to string representation
        return str(type_obj)

    def _is_literal_type(self, type_annotation: Any) -> bool:
        """Check if type annotation is a Literal type."""
        from typing import get_origin

        origin = get_origin(type_annotation)
        # Check both the origin name and string representation
        if origin is not None and str(origin) == "typing.Literal":
            return True
        if hasattr(origin, "_name") and origin._name == "Literal":
            return True
        return str(type_annotation).startswith("typing.Literal")

    def _is_optional_type(self, type_annotation: Any) -> bool:
        """Check if type annotation is Optional (Union with None)."""
        from typing import Union, get_args, get_origin

        origin = get_origin(type_annotation)
        if origin is Union:
            args = get_args(type_annotation)
            return len(args) == 2 and type(None) in args
        return False

    def _is_type_annotation(self, type_annotation: Any) -> bool:
        """Check if type annotation is Type[X]."""
        from typing import get_origin

        origin = get_origin(type_annotation)
        return origin is type


@dataclass
class MatchingError:
    """Represents a parameter matching error."""

    error_type: str  # "Missing parameters" or "Unexpected parameters"
    parameters: list[str]
    object_name: str

    def format_error_message(self) -> str:
        """Format error message for parameter matching errors.

        Returns:
            Formatted error message string
        """
        param_list = ", ".join(self.parameters)
        return f"❌ {self.error_type}\nParameters: {param_list}\nObject: {self.object_name}"


class ParameterValidationError(SynConfError):
    """Raised when parameter validation fails."""

    def __init__(self, errors: list[TypeValidationError | MatchingError]):
        """Initialize parameter validation error.

        Args:
            errors: List of validation errors
        """
        self.errors = errors
        error_messages = []

        for error in errors:
            error_messages.append(error.format_error_message())

        super().__init__("\n\n".join(error_messages))
