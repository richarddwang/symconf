"""SymConf configuration object module."""

from copy import copy, deepcopy
from typing import Any, Dict, List, Optional

from .utils import import_object


class SymConfConfig:
    """Configuration object supporting both dict and attribute access."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize configuration object.

        Args:
            data: Configuration data dictionary  # (nested dict with config values)
        """
        # Store the actual data in __dict__ to enable attribute access
        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively convert nested dicts to SymConfConfig
                self.__dict__[key] = SymConfConfig(value)
            elif isinstance(value, list) and any(isinstance(item, dict) for item in value):
                # Convert dict items in lists to SymConfConfig
                self.__dict__[key] = [SymConfConfig(item) if isinstance(item, dict) else item for item in value]
            else:
                # Store primitive values directly
                self.__dict__[key] = value

    def __getitem__(self, key: str) -> Any:
        """Dict-style getter."""
        return self.__dict__[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-style setter."""
        if isinstance(value, dict):
            self.__dict__[key] = SymConfConfig(value)
        else:
            self.__dict__[key] = value

    def __delitem__(self, key: str) -> None:
        """Dict-style deleter."""
        del self.__dict__[key]

    def __contains__(self, key: str) -> bool:
        """Dict-style contains check."""
        return key in self.__dict__

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style get with default."""
        return self.__dict__.get(key, default)

    def pop(self, key: str, default: Any = None) -> Any:
        """Dict-style pop."""
        return self.__dict__.pop(key, default)

    def keys(self):
        """Return keys like a dict."""
        return self.__dict__.keys()

    def values(self):
        """Return values like a dict."""
        return self.__dict__.values()

    def items(self):
        """Return items like a dict."""
        return self.__dict__.items()

    @property
    def kwargs(self) -> Dict[str, Any]:
        """Get kwargs dict with special keys filtered out.

        Returns:
            Dictionary suitable for **kwargs unpacking  # (filtered config dict)
        """
        filtered = {}  # Dict[str, Any] (kwargs-ready dictionary)

        # Filter out special keys and convert nested configs
        for key, value in self.__dict__.items():
            if key in ["TYPE", "CLASS"]:
                continue  # Skip special configuration keys
            if isinstance(value, SymConfConfig):
                # Convert nested SymConfConfig to plain dict
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
                config._set_nested_value(key_path, value)
            return config.realize()  # Realize with applied overwrites
        
        # Handle configurations without TYPE (not object definitions)
        if "TYPE" not in self.__dict__:
            # No TYPE, just return SymConfConfig with realized children
            result = {}  # Dict[str, Any] (processed configuration values)
            for key, value in self.__dict__.items():
                if isinstance(value, SymConfConfig):
                    # Recursively realize nested configurations
                    result[key] = value.realize(overwrites)
                else:
                    # Keep primitive values as-is
                    result[key] = value
            return SymConfConfig(result)

        # Realize the object with TYPE
        return self._realize_single_object(self)

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
                if isinstance(value, SymConfConfig):
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

    def _set_nested_value(self, key_path: str, value: Any) -> None:
        """Set nested value using dot notation.

        Args:
            key_path: Dot-separated key path  # (e.g., "parent.child.grandchild")
            value: Value to set  # (value to assign at the path)
        """
        keys = key_path.split(".")  # Split path into individual keys
        current = self

        # Navigate to parent of target key, creating nested dicts as needed
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def _realize_single_object(self, config: "SymConfConfig") -> Any:
        """Realize a single object from configuration.

        Args:
            config: Configuration object with TYPE key

        Returns:
            Realized object  # (instantiated object)
        """
        # Handle different object types
        if "CLASS" in config:
            # Instance method case - create instance first, then call method
            assert "." in config["TYPE"], "TYPE must be in '<class>.<method>' format when using CLASS"
            class_path, method_name = config["TYPE"].rsplit(".", 1)

            # Create the class instance
            class_config = copy(config['CLASS'])
            class_config['TYPE'] = class_path
            instance = class_config.realize()
            obj = getattr(instance, method_name)
        else:
            obj = import_object(config["TYPE"])

        # Regular class/function instantiation
        kwargs = {k: v for k, v in config.items() if k not in ["TYPE", "CLASS"]}

        # Realize nested objects in kwargs (depth-first)
        for key, value in kwargs.items():
            if isinstance(value, dict | SymConfConfig) and "TYPE" in value:
                kwargs[key] = self._realize_single_object(value)

        return obj(**kwargs)

    def _to_dict(self) -> Dict[str, Any]:
        """Convert to plain dictionary.

        Returns:
            Plain dictionary representation  # (nested dict without SymConfConfig wrappers)
        """
        result = {}  # Dict[str, Any] (plain dictionary)

        # Convert all values recursively
        for key, value in self.__dict__.items():
            if isinstance(value, SymConfConfig):
                # Recursively convert nested SymConfConfig
                result[key] = value._to_dict()
            elif isinstance(value, list):
                # Handle lists with potential SymConfConfig items
                result[key] = [item._to_dict() if isinstance(item, SymConfConfig) else item for item in value]
            else:
                # Keep primitive values as-is
                result[key] = value
        return result

    def __repr__(self) -> str:
        """String representation."""
        return f"SymConfConfig({self._to_dict()})"
