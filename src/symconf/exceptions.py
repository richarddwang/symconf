"""Custom exceptions for SymConf."""

from dataclasses import dataclass
from typing import Any, Optional


class SymConfError(Exception):
    """Base exception for SymConf errors."""

    pass


class CircularInterpolationError(SymConfError):
    """Raised when circular dependencies are detected in interpolation."""

    def __init__(self, cycle_path: list[str]):
        self.cycle_path = cycle_path
        cycle_display = " → ".join(cycle_path)
        super().__init__(f"Circular interpolation detected: {cycle_display} → {cycle_path[0]}")


class CircularKwargsChainError(SymConfError):
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
    expected: str
    actual_value: Any
    actual_type: Optional[str] = None

    def format_error_message(self) -> str:
        """Format error message for type mismatch.

        Returns:
            Formatted error message string
        """
        actual_line = self._format_actual_value(self.actual_value, self.actual_type)
        return f"❌ Type mismatch\nParameter: {self.parameter}\nExpected: {self.expected}\nActual: {actual_line}"

    def _format_actual_value(self, actual_value: Any, actual_type: Optional[str]) -> str:
        """Format actual value and type for error messages.

        Args:
            actual_value: The actual value
            actual_type: The actual type string

        Returns:
            Formatted value and type string
        """
        if actual_value is None:
            return "None (NoneType)"

        # Handle class types
        if isinstance(actual_value, type):
            return f"`{actual_value.__name__}`"

        # Handle class instances
        if hasattr(actual_value, "__class__") and hasattr(actual_value.__class__, "__name__"):
            if not isinstance(actual_value, (str, int, float, bool, list, dict, tuple)):
                return f"`{actual_value.__class__.__name__}`"

        # Handle string values
        if isinstance(actual_value, str):
            return f"'{actual_value}' (str)"

        # Default formatting
        return f"{actual_value} ({actual_type or type(actual_value).__name__})"


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


class ParameterValidationError(SymConfError):
    """Raised when parameter validation fails."""

    def __init__(self, errors: list[TypeValidationError | MatchingError]):
        """Initialize parameter validation error.

        Args:
            errors: List of validation errors
        """
        self.errors = errors
        error_messages = [""]  # Start with empty line

        for error in errors:
            error_messages.append(error.format_error_message())
            error_messages.append("")  # Empty line between errors

        super().__init__("\n".join(error_messages))
