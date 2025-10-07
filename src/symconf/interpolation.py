import os
import re
from typing import Any, Dict, Set

from .exceptions import CircularInterpolationError


class InterpolationEngine:
    """Engine for variable interpolation."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize interpolation engine.

        Args:
            config: Configuration data

        Note:
            Environment variables are accessed from os.environ directly
        """
        self.config = config
        self.resolving: Set[str] = set()

    def resolve_all_interpolations(self) -> Dict[str, Any]:
        """Resolve all interpolations in the configuration in-place.

        Returns:
            Configuration with all interpolations resolved
        """
        self._resolve_recursive(self.config)
        return self.config

    def _resolve_recursive(self, data: Any, current_path: str = "") -> None:
        """Recursively resolve interpolations in-place.

        Args:
            data: Data to process (modified in-place)
            current_path: Current parameter path for cycle detection
        """
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{current_path}.{key}" if current_path else key
                if isinstance(value, str) and "${" in value:
                    # Resolve interpolation and update in-place
                    data[key] = self._resolve_value(value, new_path)
                else:
                    # Recursively process nested structures
                    self._resolve_recursive(value, new_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str) and "${" in item:
                    # Resolve interpolation and update in-place
                    data[i] = self._resolve_value(item, current_path)
                else:
                    # Recursively process nested structures
                    self._resolve_recursive(item, current_path)

    def _resolve_value(self, value: str, current_path: str = "") -> Any:
        """Resolve all interpolations in a string value.

        Args:
            value: String value containing interpolations
            current_path: Current parameter path for cycle detection

        Returns:
            Resolved value

        Raises:
            CircularInterpolationError: If circular dependency is detected
        """
        # Check for circular dependency
        if current_path and current_path in self.resolving:
            cycle = list(self.resolving) + [current_path]
            raise CircularInterpolationError(cycle)

        # Find all interpolation matches
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, value)

        if not matches:
            return value

        # Add to resolving set if we have a path
        if current_path:
            self.resolving.add(current_path)

        try:
            result = value
            for match in matches:
                # Resolve the match
                replacement = self._resolve_match(match)
                result = result.replace(f"${{{match}}}", str(replacement))

            # Try to convert to appropriate type if it's a pure substitution
            if isinstance(result, str):
                if result.isdigit():
                    result = int(result)
                elif self._is_float(result):
                    result = float(result)

            return result
        finally:
            # Remove from resolving set
            if current_path:
                self.resolving.discard(current_path)

    def _resolve_match(self, match: str) -> Any:
        """Resolve a single interpolation match.

        Args:
            match: The interpolation content (without ${})

        Returns:
            Resolved value

        Raises:
            ValueError: If environment variable not found or expression evaluation fails
        """
        # Expression interpolation (contains backticks)
        if "`" in match:
            return self._resolve_expression(match)

        # Environment variable interpolation (all uppercase)
        if match.isupper():
            if match in os.environ:
                env_value = os.environ[match]
                # Try to convert to number if possible
                if env_value.isdigit():
                    return int(env_value)
                elif self._is_float(env_value):
                    return float(env_value)
                return env_value
            else:
                raise ValueError(f"Environment variable '{match}' not found")

        # Parameter interpolation (cross-reference)
        return self._get_value_of_param(match)

    def _resolve_expression(self, expr: str) -> Any:
        """Resolve expression interpolation with backtick variables.

        Args:
            expr: Expression with backtick variables

        Returns:
            Evaluated result

        Raises:
            ValueError: If expression contains unsafe operations or evaluation fails
        """
        # Replace `var.path` with actual values
        pattern = r"`([^`]+)`"

        def replace_var(m):
            var_path = m.group(1)
            value = self._get_value_of_param(var_path)
            return str(value)

        interpolated_expr = re.sub(pattern, replace_var, expr)
        return eval(interpolated_expr)

    def _get_raw_value_for_param(self, key_path: str) -> Any:
        """Get raw value from nested dict using dot notation (no interpolation resolution).

        Args:
            key_path: Dot-separated key path

        Returns:
            Raw value at the specified path

        Raises:
            KeyError: If key path is not found
        """
        keys = key_path.split(".")
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise KeyError(f"Key path '{key_path}' not found")
        return value

    def _get_value_of_param(self, key_path: str) -> Any:
        """Get value from nested dict using dot notation with full interpolation resolution.

        Args:
            key_path: Dot-separated key path

        Returns:
            Value at the specified path, with all interpolations resolved

        Raises:
            KeyError: If key path is not found
            CircularInterpolationError: If circular dependency is detected
        """
        # Check if we're already resolving this key (circular dependency)
        if key_path in self.resolving:
            cycle = list(self.resolving) + [key_path]
            raise CircularInterpolationError(cycle)

        # Get raw value from config
        raw_value = self._get_raw_value_for_param(key_path)

        # If value contains interpolation, resolve it using the unified resolver
        if isinstance(raw_value, str) and "${" in raw_value:
            resolved_value = self._resolve_value(raw_value, key_path)
        else:
            resolved_value = raw_value

        return resolved_value

    def _is_float(self, s: str) -> bool:
        """Check if string represents a float.

        Args:
            s: String to check

        Returns:
            True if string represents a float
        """
        try:
            float(s)
            return True
        except ValueError:
            return False
