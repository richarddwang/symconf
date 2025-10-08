"""Variable interpolation engine for SymConf configurations."""

import os
import re
from typing import Any, Dict, Set

from .exceptions import CircularInterpolationError


class InterpolationEngine:
    """Engine for variable interpolation."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize interpolation engine.

        Args:
            config: Configuration data  # (nested dict with string interpolations)

        Note:
            Environment variables are accessed from os.environ directly
        """
        self.config = config  # (nested dict containing configuration values)
        self.resolving: Set[str] = set()  # (parameter paths currently being resolved for cycle detection)

    def resolve_all_interpolations(self) -> Dict[str, Any]:
        """Resolve all interpolations in the configuration in-place.

        Returns:
            Configuration with all interpolations resolved  # (nested dict with interpolations replaced)
        """
        # Process the entire configuration tree recursively
        self._resolve_recursive(self.config)
        return self.config

    def _resolve_recursive(self, data: Any, current_path: str = "") -> None:
        """Recursively resolve interpolations in-place.

        Args:
            data: Data to process (modified in-place)  # (dict, list, or scalar value)
            current_path: Current parameter path for cycle detection  # (dot-separated path)
        """
        # Handle dictionary structures
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{current_path}.{key}" if current_path else key
                if isinstance(value, str) and "${" in value:
                    # Resolve interpolation and update in-place
                    data[key] = self._resolve_value(value, new_path)
                else:
                    # Recursively process nested structures
                    self._resolve_recursive(value, new_path)
        # Handle list structures
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
            value: String value containing interpolations  # (string with ${...} patterns)
            current_path: Current parameter path for cycle detection  # (dot-separated path)

        Returns:
            Resolved value  # (string, int, float, or other type after resolution)

        Raises:
            CircularInterpolationError: If circular dependency is detected
        """
        # Check for circular dependency
        if current_path and current_path in self.resolving:
            cycle = list(self.resolving) + [current_path]
            raise CircularInterpolationError(cycle)

        # Find all interpolation matches using regex pattern
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, value)

        # No interpolations found, return as-is
        if not matches:
            return value

        # Add to resolving set if we have a path (for cycle detection)
        if current_path:
            self.resolving.add(current_path)

        try:
            result = value
            # Resolve each interpolation match
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
            # Remove from resolving set (cleanup)
            if current_path:
                self.resolving.discard(current_path)

    def _resolve_match(self, match: str) -> Any:
        """Resolve a single interpolation match.

        Args:
            match: The interpolation content (without ${})  # (content inside ${...})

        Returns:
            Resolved value  # (environment value, parameter value, or expression result)

        Raises:
            ValueError: If environment variable not found or expression evaluation fails
        """
        # Expression interpolation (contains backticks for variable references)
        if "`" in match:
            return self._resolve_expression(match)

        # Environment variable interpolation (all uppercase convention)
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

        # Parameter interpolation (cross-reference to other config parameters)
        return self._get_value_of_param(match)

    def _resolve_expression(self, expr: str) -> Any:
        """Resolve expression interpolation with backtick variables.

        Args:
            expr: Expression with backtick variables  # (math expression with `var.path` references)

        Returns:
            Evaluated result  # (numeric result of expression evaluation)

        Raises:
            ValueError: If expression contains unsafe operations or evaluation fails
        """
        # Replace `var.path` with actual values using regex substitution
        pattern = r"`([^`]+)`"

        def replace_var(m):
            var_path = m.group(1)
            value = self._get_value_of_param(var_path)
            return str(value)

        # Substitute all backtick variables with their values
        interpolated_expr = re.sub(pattern, replace_var, expr)
        # Evaluate the final expression
        return eval(interpolated_expr)

    def _get_raw_value_for_param(self, key_path: str) -> Any:
        """Get raw value from nested dict using dot notation (no interpolation resolution).

        Args:
            key_path: Dot-separated key path  # (e.g., "parent.child.grandchild")

        Returns:
            Raw value at the specified path  # (unprocessed value from config)

        Raises:
            KeyError: If key path is not found
        """
        keys = key_path.split(".")  # Split path into individual keys
        value = self.config

        # Navigate through nested dictionary structure
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise KeyError(f"Key path '{key_path}' not found")
        return value

    def _get_value_of_param(self, key_path: str) -> Any:
        """Get value from nested dict using dot notation with full interpolation resolution.

        Args:
            key_path: Dot-separated key path  # (e.g., "parent.child.grandchild")

        Returns:
            Value at the specified path, with all interpolations resolved  # (fully processed value)

        Raises:
            KeyError: If key path is not found
            CircularInterpolationError: If circular dependency is detected
        """
        # Check if we're already resolving this key (circular dependency detection)
        if key_path in self.resolving:
            cycle = list(self.resolving) + [key_path]
            raise CircularInterpolationError(cycle)

        # Get raw value from config
        raw_value = self._get_raw_value_for_param(key_path)

        # If value contains interpolation, resolve it using the unified resolver
        if isinstance(raw_value, str) and "${" in raw_value:
            resolved_value = self._resolve_value(raw_value, key_path)
        else:
            # Value doesn't need interpolation
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
