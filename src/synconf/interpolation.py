"""Variable interpolation engine for SynConf configurations."""

import os
import re
from typing import Any, Dict, Set

from synconf.utils import load_yaml

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
                if isinstance(value, str) and "((" in value:
                    # Resolve interpolation and update in-place
                    data[key] = self._resolve_value(value, new_path)
                else:
                    # Recursively process nested structures
                    self._resolve_recursive(value, new_path)
        # Handle list structures
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str) and "((" in item:
                    # Resolve interpolation and update in-place
                    data[i] = self._resolve_value(item, current_path)
                else:
                    # Recursively process nested structures
                    self._resolve_recursive(item, current_path)

    def _resolve_value(self, value: str, key_path: str) -> Any:
        """Resolve all interpolations in a string value.

        Args:
            value: String value containing interpolations  # (string with ((...)) patterns)
            key_path: Current parameter path  # (dot-separated path)

        Returns:
            Resolved value  # (string, int, float, or other type after resolution)

        Raises:
            CircularInterpolationError: If circular dependency is detected
        """
        # Check for circular dependency
        if key_path in self.resolving:
            cycle = list(self.resolving) + [key_path]
            raise CircularInterpolationError(cycle)
        else:
            self.resolving.add(key_path)

        pattern = r"\(\((.+?)\)\)(?:[^\)]|$)"
        matches = re.findall(pattern, value)

        # No interpolations found, return as-is
        if not matches:
            result = value

        # Full string is a single interpolation e.g., model: ((ENV_VAR)) or model: ((param.path)) or model: ((`1 + 2`))
        elif re.fullmatch(pattern, value):
            result = self._resolve_match(matches[0])

        # Mixed content with one or more interpolations e.g., model: resnet_((ENV_VAR))_v2 or model: resnet_((param.path))_v2 or model: resnet_((`1 + 2`))_v2
        else:
            # Resolve each interpolation match
            result = value
            for match in matches:
                replacement = self._resolve_match(match)
                result = result.replace(f"(({match}))", str(replacement))

        # Just like it is written in yaml, convert to appropriate type if possible
        if isinstance(result, str):
            result = load_yaml(result)

        self.resolving.discard(key_path)
        return result

    def _resolve_match(self, match: str) -> Any:
        """Resolve a single interpolation match.

        Args:
            match: The interpolation content (without ${})  # (content inside ${...})

        Returns:
            Resolved value # (environment value, parameter value, or expression result)

        Raises:
            ValueError: If environment variable not found or expression evaluation fails
        """
        # Expression interpolation (contains backticks for variable references)
        if "`" in match:
            value = self._resolve_expression(match)
        # Variable interpolation (cross-reference to other config parameters or environment variables)
        else:
            value = self._get_value_of_param(match)

        return value

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
            key_path: Dot-separated key path or environment variable name e.g., "parent.child.grandchild"

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

        # Check if this is an environment variable (all uppercase convention)
        if key_path.isupper():
            return os.environ[key_path]

        # Get raw value from config
        raw_value = self._get_raw_value_for_param(key_path)

        # If value contains interpolation, resolve it using the unified resolver
        if isinstance(raw_value, str) and "((" in raw_value:
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
