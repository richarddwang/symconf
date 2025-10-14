"""SynConf configuration object module."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from .utils import import_object


class SynConfig:
    """Configuration object supporting both dict and attribute access."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize configuration object.

        Args:
            data: Configuration data dictionary  # (nested dict with config values)
        """
        # Store the actual data in __dict__ to enable attribute access
        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively convert nested dicts to SynConfig
                self.__dict__[key] = SynConfig(value)
            elif isinstance(value, list) and any(isinstance(item, dict) for item in value):
                # Convert dict items in lists to SynConfig
                self.__dict__[key] = [SynConfig(item) if isinstance(item, dict) else item for item in value]
            else:
                # Store primitive values directly
                self.__dict__[key] = value

    def __getitem__(self, key: str) -> "SynConfig" | Any:
        """Dict-style getter with support for dot notation paths."""
        return self._get_nested_value(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-style setter with support for dot notation paths."""
        # Convert nested structures to maintain consistency with __init__
        value = self._convert_nested_structures(value)
        self._nestedly_set_value(key, value)

    def __delitem__(self, key: str) -> None:
        """Dict-style deleter with support for dot notation paths."""
        self._delete_nested_value(key)

    def __contains__(self, key: str) -> bool:
        """Dict-style contains check with support for dot notation paths."""
        return self._nestedly_contains_key(key)

    def get(self, key: str, default: Any = None) -> "SynConfig" | Any:
        """Dict-style get with default and support for dot notation paths."""
        try:
            return self._get_nested_value(key)
        except (KeyError, AttributeError):
            return default

    def pop(self, key: str, *args) -> "SynConfig" | Any:
        """Dict-style pop with support for dot notation paths."""
        return self._nestedly_pop_value(key, *args)

    def keys(self):
        """Return keys like a dict."""
        return self.__dict__.keys()

    def values(self):
        """Return values like a dict."""
        return self.__dict__.values()

    def items(self):
        """Return items like a dict."""
        return self.__dict__.items()

    def __getattr__(self, name: str) -> "SynConfig" | Any:
        """Attribute-style getter with support for dot notation paths."""
        try:
            return self._get_nested_value(name)
        except KeyError as e:
            # Convert KeyError to AttributeError with more specific message about the key path
            raise AttributeError(f"Key path '{name}' does not exist") from e

    def __setattr__(self, name: str, value: Any) -> None:
        """Attribute-style setter with support for dot notation paths."""
        # Convert nested structures to maintain consistency with __init__
        value = self._convert_nested_structures(value)
        self._nestedly_set_value(name, value)

    def __delattr__(self, name: str) -> None:
        """Attribute-style deleter with support for dot notation paths."""
        try:
            self._delete_nested_value(name)
        except KeyError as e:
            # Convert KeyError to AttributeError for consistency with Python's attribute access
            raise AttributeError(f"Key path '{name}' does not exist") from e

    @property
    def kwargs(self) -> Dict[str, Any]:
        """Get kwargs dict with special keys filtered out.

        Returns:
            Dictionary suitable for **kwargs unpacking  # (filtered config dict)
        """
        filtered = {}  # Dict[str, Any] (kwargs-ready dictionary)

        # Filter out special keys and convert nested configs
        for key, value in self.__dict__.items():
            if key in ["TYPE", "self"]:
                continue  # Skip special configuration keys
            if isinstance(value, SynConfig):
                # Convert nested SynConfig to plain dict
                filtered[key] = value._to_dict()
            else:
                # Use value as-is
                filtered[key] = value
        return filtered

    def realize(self, overwrites: Optional[Dict[str, Any]] = None) -> Any:
        """Realize object(s) from configuration.

        Args:
            overwrites: Optional parameter overwrites using dot notation  # (key-value overrides)

        Returns:
            Realized object or updated configuration  # (instantiated object or config)
        """
        if overwrites:
            config = deepcopy(self)  # Ensure original config is not modified
            for key_path, value in overwrites.items():
                config._nestedly_set_value(key_path, value)
            return config.realize()  # Realize with applied overwrites

        # Handle configurations without TYPE (not object definitions)
        if "TYPE" not in self.__dict__:
            # No TYPE, just return SynConfig with realized children
            result = {}  # Dict[str, Any] (processed configuration values)
            for key, value in self.__dict__.items():
                if isinstance(value, SynConfig):
                    # Recursively realize nested configurations
                    result[key] = value.realize(overwrites)
                else:
                    # Keep primitive values as-is
                    result[key] = value
            return SynConfig(result)

        # Realize the object with TYPE
        return self._realize_single_object(self)

    def resolve_type(self) -> Any:
        """Resolve the TYPE to get the actual object/method for manual realization.

        Returns:
            The actual callable object (class, function, or method)

        Raises:
            KeyError: If TYPE is not present
        """
        if "TYPE" not in self.__dict__:
            raise KeyError("Cannot resolve type: no TYPE specified")

        return import_object(self["TYPE"])

    def pretty(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Serialize configuration to flattened format.

        Args:
            exclude: List of parameter paths to exclude  # (dot-notation paths to skip)

        Returns:
            Flattened configuration dictionary  # (flattened key-value mapping)
        """
        exclude = exclude or []
        result = {}  # Dict[str, Any] (flattened configuration)

        def _flatten(data: Dict[str, Any], prefix: str = "") -> None:
            """Recursively flatten nested configuration data.

            Args:
                data: Data to flatten  # (nested dict structure)
                prefix: Current key prefix  # (dot-separated path prefix)
            """
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key

                # Skip excluded paths
                if full_key in exclude:
                    continue

                # Handle nested structures
                if isinstance(value, SynConfig):
                    _flatten(value._to_dict(), full_key)
                elif isinstance(value, dict):
                    _flatten(value, full_key)
                else:
                    # Convert objects back to their type string if possible
                    if hasattr(value, "__class__") and hasattr(value.__class__, "__module__"):
                        if value.__class__.__module__ != "builtins":
                            class_name = f"{value.__class__.__module__}.{value.__class__.__name__}"
                            result[full_key] = class_name
                        else:
                            result[full_key] = value
                    else:
                        result[full_key] = value

        # Start flattening from root level
        _flatten(self._to_dict())
        return result

    def _get_nested_value(self, key_path: str) -> Any:
        """Get value using key path (supports both simple and nested keys).

        Args:
            key_path: Key path (simple key or dot-separated path)  # (e.g., "key" or "parent.child.grandchild")

        Returns:
            Value at the specified path

        Raises:
            KeyError: If path doesn't exist
        """
        keys = key_path.split(".")  # Split path into individual keys
        current = self

        # Navigate through the path
        for key in keys:
            if isinstance(current, SynConfig):
                if key not in current.__dict__:
                    raise KeyError(f"Key '{key}' not found in path '{key_path}'")
                current = current.__dict__[key]
            else:
                raise KeyError(f"Cannot access '{key}' on non-config object in path '{key_path}'")

        return current

    def _delete_nested_value(self, key_path: str) -> None:
        """Delete value using key path (supports both simple and nested keys).

        Args:
            key_path: Key path (simple key or dot-separated path)  # (e.g., "key" or "parent.child.grandchild")

        Raises:
            KeyError: If path doesn't exist
        """
        keys = key_path.split(".")  # Split path into individual keys
        current = self

        # Navigate to parent of target key
        for key in keys[:-1]:
            if isinstance(current, SynConfig):
                if key not in current.__dict__:
                    raise KeyError(f"Key '{key}' not found in path '{key_path}'")
                current = current.__dict__[key]
            else:
                raise KeyError(f"Cannot access '{key}' on non-config object in path '{key_path}'")

        # Delete the final key
        if isinstance(current, SynConfig):
            if keys[-1] not in current.__dict__:
                raise KeyError(f"Key '{keys[-1]}' not found in path '{key_path}'")
            del current.__dict__[keys[-1]]
        else:
            raise KeyError(f"Cannot delete '{keys[-1]}' on non-config object in path '{key_path}'")

    def _nestedly_set_value(self, key_path: str, value: Any) -> None:
        """Set value using key path (supports both simple and nested keys).

        Args:
            key_path: Key path (simple key or dot-separated path)  # (e.g., "key" or "parent.child.grandchild")
            value: Value to set  # (value to assign at the path)
        """
        keys = key_path.split(".")  # Split path into individual keys
        current = self

        # Navigate to parent of target key, creating nested dicts as needed
        for key in keys[:-1]:
            if key not in current.__dict__:
                current.__dict__[key] = SynConfig({})
            current = current.__dict__[key]

        # Set the final value directly in __dict__ to avoid recursion
        # Note: value should already be converted by the calling method
        current.__dict__[keys[-1]] = value

    def _nestedly_pop_value(self, key_path: str, *args) -> Any:
        """Pop value using key path (supports both simple and nested keys).

        Args:
            key_path: Key path (simple key or dot-separated path)  # (e.g., "key" or "parent.child.grandchild")
            *args: Optional default value (matching dict.pop signature)

        Returns:
            The popped value or default if key doesn't exist

        Raises:
            KeyError: If key doesn't exist and no default provided
        """
        try:
            # Get the value first
            value = self._get_nested_value(key_path)
            # Then delete it
            self._delete_nested_value(key_path)
            return value
        except KeyError:
            if args:
                return args[0]  # Return default if provided
            raise  # Re-raise KeyError if no default provided

    def _nestedly_contains_key(self, key_path: str) -> bool:
        """Check if key path exists (supports both simple and nested keys).

        Args:
            key_path: Key path (simple key or dot-separated path)  # (e.g., "key" or "parent.child.grandchild")

        Returns:
            True if key path exists, False otherwise
        """
        keys = key_path.split(".")  # Split path into individual keys
        current = self

        # Navigate through the path
        for key in keys:
            if isinstance(current, SynConfig):
                if key not in current.__dict__:
                    return False
                current = current.__dict__[key]
            else:
                return False

        return True

    def _convert_nested_structures(self, value: Any) -> Any:
        """Convert nested dicts and lists containing dicts to SynConfig objects.

        This ensures consistency between __init__ and setter methods.

        Args:
            value: Value to convert  # (any value that might contain nested structures)

        Returns:
            Converted value with nested structures as SynConfig objects
        """
        if isinstance(value, dict):
            # Convert dict to SynConfig
            return SynConfig({k: self._convert_nested_structures(v) for k, v in value.items()})
        elif isinstance(value, list):
            # Recursively process list items that might contain nested structures
            return [self._convert_nested_structures(item) for item in value]
        else:
            # Return primitive values as-is
            return value

    def _is_instance_method(self, type_path: str) -> bool:
        """Check if TYPE refers to an instance method.

        Args:
            type_path: TYPE string to check

        Returns:
            True if this is an instance method
        """
        if "." not in type_path:
            return False

        # Try to import the object directly
        obj = import_object(type_path)

        # Check if this is an unbound instance method
        import inspect

        if inspect.isfunction(obj):
            sig = inspect.signature(obj)
            params = list(sig.parameters.keys())
            # If first parameter is 'self', it's likely an instance method
            if params and params[0] == "self":
                return True

    def _realize_single_object(self, config: "SynConfig") -> Any:
        """Realize a single object from configuration.

        Args:
            config: Configuration object with TYPE key

        Returns:
            Realized object  # (instantiated object)
        """

        # Realize nested objects in kwargs (depth-first)
        kwargs = {k: v for k, v in config.items() if k not in ["TYPE"]}
        for key, value in kwargs.items():
            if isinstance(value, dict | SynConfig) and "TYPE" in value:
                kwargs[key] = self._realize_single_object(value)

        # Import the object (class, function, or method) and realize it
        obj = import_object(config["TYPE"])
        return obj(**kwargs)

    def _to_dict(self) -> Dict[str, Any]:
        """Convert to plain dictionary.

        Returns:
            Plain dictionary representation  # (nested dict without SynConfig wrappers)
        """
        result = {}  # Dict[str, Any] (plain dictionary)

        # Convert all values recursively
        for key, value in self.__dict__.items():
            if isinstance(value, SynConfig):
                # Recursively convert nested SynConfig
                result[key] = value._to_dict()
            elif isinstance(value, list):
                # Handle lists with potential SynConfig items
                result[key] = [item._to_dict() if isinstance(item, SynConfig) else item for item in value]
            else:
                # Keep primitive values as-is
                result[key] = value
        return result

    def __repr__(self) -> str:
        """String representation."""
        return f"SynConfig({self._to_dict()})"
