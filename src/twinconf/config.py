"""Configuration object implementation for TwinConf."""

import copy
import importlib
from typing import Any, Dict, List, Optional


class ConfigurationObject(dict):
    """A dictionary-like object that supports both dict-style and attribute-style access.

    This class provides the core configuration object that supports:
    - Dict-style access: config['key']
    - Attribute-style access: config.key
    - Object realization: config.realize()
    - Pretty serialization: config.pretty()
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the configuration object.

        Args:
            data: Initial configuration data
        """
        if data is None:
            data = {}
        super().__init__(data)
        self._convert_nested_dicts()

    def _convert_nested_dicts(self) -> None:
        """Convert nested dictionaries to ConfigurationObject instances."""
        for key, value in list(self.items()):
            if isinstance(value, dict) and not isinstance(value, ConfigurationObject):
                self[key] = ConfigurationObject(value)
            elif isinstance(value, list):
                self[key] = [
                    ConfigurationObject(item)
                    if isinstance(item, dict) and not isinstance(item, ConfigurationObject)
                    else item
                    for item in value
                ]

    def __getattr__(self, key: str) -> Any:
        """Enable attribute-style access for getting values."""
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")

    def __setattr__(self, key: str, value: Any) -> None:
        """Enable attribute-style access for setting values."""
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self[key] = value
            if isinstance(value, dict) and not isinstance(value, ConfigurationObject):
                self[key] = ConfigurationObject(value)
            elif isinstance(value, list):
                self[key] = [
                    ConfigurationObject(item)
                    if isinstance(item, dict) and not isinstance(item, ConfigurationObject)
                    else item
                    for item in value
                ]

    def __delattr__(self, key: str) -> None:
        """Enable attribute-style access for deleting values."""
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")

    def __setitem__(self, key: str, value: Any) -> None:
        """Override setitem to convert nested dicts to ConfigurationObject."""
        super().__setitem__(key, value)
        if isinstance(value, dict) and not isinstance(value, ConfigurationObject):
            super().__setitem__(key, ConfigurationObject(value))
        elif isinstance(value, list):
            super().__setitem__(
                key,
                [
                    ConfigurationObject(item)
                    if isinstance(item, dict) and not isinstance(item, ConfigurationObject)
                    else item
                    for item in value
                ],
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value with an optional default."""
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key: str, default: Any = None) -> Any:
        """Remove and return a value with an optional default."""
        try:
            return super().pop(key)
        except KeyError:
            if default is not None:
                return default
            raise

    @property
    def kwargs(self) -> Dict[str, Any]:
        """Get configuration as keyword arguments, excluding special keys like TYPE.

        Returns:
            Dictionary of arguments suitable for object initialization
        """
        result = {}
        for key, value in self.items():
            if key not in ("TYPE", "CLASS", "MERGE"):
                if isinstance(value, ConfigurationObject):
                    result[key] = dict(value)
                else:
                    result[key] = value
        return result

    def realize(self, overwrites: Optional[Dict[str, Any]] = None) -> Any:
        """Realize configuration objects into actual instances.

        Args:
            overwrites: Optional dictionary of overwrites using nested keys

        Returns:
            Realized object instance or configuration object
        """
        # Apply overwrites if provided
        config = copy.deepcopy(self)
        if overwrites:
            config = self._apply_overwrites(config, overwrites)

        # Handle LIST type specially
        if config.get("TYPE") == "LIST":
            from .utils import process_list_type

            return process_list_type(config)

        # If this configuration has a TYPE, realize it as an object
        if "TYPE" in config:
            return self._realize_object(config)

        # Otherwise, recursively realize any nested objects
        result = {}
        for key, value in config.items():
            if isinstance(value, ConfigurationObject):
                result[key] = value.realize()
            elif isinstance(value, list):
                result[key] = [item.realize() if isinstance(item, ConfigurationObject) else item for item in value]
            else:
                result[key] = value

        return ConfigurationObject(result)

    def _apply_overwrites(self, config: "ConfigurationObject", overwrites: Dict[str, Any]) -> "ConfigurationObject":
        """Apply overwrites using nested key notation."""
        for key_path, value in overwrites.items():
            keys = key_path.split(".")
            current = config

            # Navigate to the parent of the target key
            for key in keys[:-1]:
                if key not in current:
                    current[key] = ConfigurationObject()
                current = current[key]

            # Set the final value
            current[keys[-1]] = value

        return config

    def _realize_object(self, config: "ConfigurationObject") -> Any:
        """Realize a single object configuration."""
        obj_type = config["TYPE"]

        # Handle string type paths
        if isinstance(obj_type, str):
            obj_type = self._import_object(obj_type)

        # Prepare arguments, recursively realizing nested objects
        kwargs = {}
        for key, value in config.items():
            if key in ("TYPE", "CLASS"):
                continue

            if isinstance(value, ConfigurationObject):
                if "TYPE" in value:
                    kwargs[key] = value.realize()
                else:
                    kwargs[key] = dict(value)
            elif isinstance(value, list):
                kwargs[key] = [
                    item.realize() if isinstance(item, ConfigurationObject) and "TYPE" in item else item
                    for item in value
                ]
            else:
                kwargs[key] = value

        # Handle instance methods
        if isinstance(config["TYPE"], str) and "." in config["TYPE"]:
            # Handle method calls like "Class.method"
            parts = config["TYPE"].split(".")
            if len(parts) >= 2:
                class_path = ".".join(parts[:-1])
                method_name = parts[-1]

                try:
                    cls = self._import_object(class_path)
                    if "CLASS" in config:
                        # Instance method call
                        class_config = config["CLASS"]
                        if isinstance(class_config, ConfigurationObject):
                            instance = cls(**class_config.kwargs)
                        else:
                            instance = cls(**class_config)
                        method = getattr(instance, method_name)
                        return method(**kwargs)
                    else:
                        # Class method or static method
                        method = getattr(cls, method_name)
                        return method(**kwargs)
                except (ImportError, AttributeError):
                    pass

        # Regular object instantiation
        return obj_type(**kwargs)

    def _import_object(self, object_path: str) -> Any:
        """Import and return an object from a module path."""
        if "." not in object_path:
            raise ImportError(f"Invalid object path: {object_path}")

        module_path, object_name = object_path.rsplit(".", 1)

        try:
            module = importlib.import_module(module_path)
            return getattr(module, object_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not import {object_path}: {e}")

    def pretty(self, exclude: Optional[List[str]] = None, prefix: str = "") -> Dict[str, Any]:
        """Generate a pretty, flattened representation of the configuration.

        Args:
            exclude: List of nested keys to exclude
            prefix: Internal parameter for recursion

        Returns:
            Flattened dictionary representation
        """
        if exclude is None:
            exclude = []

        result = {}

        for key, value in self.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if full_key in exclude:
                continue

            if isinstance(value, ConfigurationObject):
                # Recursively flatten nested configurations
                nested = value.pretty(exclude=exclude, prefix=full_key)
                result.update(nested)
            elif isinstance(value, type):
                # Convert types to their string representation
                result[full_key] = (
                    f"{value.__module__}.{value.__name__}" if hasattr(value, "__module__") else str(value)
                )
            elif (
                hasattr(value, "__class__")
                and hasattr(value.__class__, "__module__")
                and value.__class__.__module__ not in ("builtins", "__main__")
            ):
                # Convert instances to their class string representation (but not basic types)
                cls = value.__class__
                result[full_key] = f"{cls.__module__}.{cls.__name__}"
            else:
                result[full_key] = value

        return result
