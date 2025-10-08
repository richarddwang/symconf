"""Custom exceptions for SymConf."""

from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Type


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
    expected_type: Type
    actual_value: Any
    actual_type: Type

    def format_error_message(self) -> str:
        """Format error message for type mismatch.

        Returns:
            Formatted error message string
        """
        return dedent(f"""\
            ❌ Type mismatch
            Parameter: {self.parameter}
            Expected: {self.expected_type}
            Actual: {self.actual_value} ({self.actual_value})\
            """)


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
