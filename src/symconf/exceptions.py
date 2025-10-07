"""Custom exceptions for SymConf."""


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


class ParameterValidationError(SymConfError):
    """Raised when parameter validation fails."""

    def __init__(self, errors: list[dict]):
        self.errors = errors
        error_messages = []
        for error in errors:
            error_messages.append(f"❌ {error['type']}")

            if error.get("parameter"):
                param_line = f"Parameter: {error['parameter']}"
                if error.get("source_info"):
                    param_line += f" ({error['source_info']})"
                error_messages.append(param_line)

            if error.get("actual") is not None or error.get("show_value_type", True):
                value_type_line = self._format_value_type(error.get("actual"), error.get("actual_type"))
                if value_type_line:
                    error_messages.append(f"Value/Type: {value_type_line}")

            if error.get("expected"):
                error_messages.append(f"Expected: {error['expected']}")

            if error.get("object_name"):
                error_messages.append(f"Object: {error['object_name']}")

            error_messages.append("")

        super().__init__("\n".join(error_messages))

    def _format_value_type(self, actual_value, actual_type: str | None) -> str:
        if actual_value is None:
            return "None (NoneType)"

        if hasattr(actual_value, "__class__") and hasattr(actual_value.__class__, "__name__"):
            if isinstance(actual_value, type):
                return f"class type of `{actual_value.__name__}`"
            elif not isinstance(actual_value, (str, int, float, bool, list, dict, tuple)):
                return f"class instance of `{actual_value.__class__.__name__}`"

        if isinstance(actual_value, str):
            return f"'{actual_value}' (str)"

        return f"{actual_value} ({actual_type or type(actual_value).__name__})"
