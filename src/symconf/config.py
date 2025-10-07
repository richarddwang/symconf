"""SymConf configuration object module."""
import copy
from typing import Any, Dict, List, Optional, Union

from .utils import import_object, deep_merge


class SymConfConfig:
    """Configuration object supporting both dict and attribute access."""
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize configuration object.
        
        Args:
            data: Configuration data dictionary
        """
        # Store the actual data in __dict__ to enable attribute access
        for key, value in data.items():
            if isinstance(value, dict):
                self.__dict__[key] = SymConfConfig(value)
            elif isinstance(value, list) and any(isinstance(item, dict) for item in value):
                self.__dict__[key] = [
                    SymConfConfig(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
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
            Dictionary suitable for **kwargs unpacking
        """
        filtered = {}
        for key, value in self.__dict__.items():
            if key in ['TYPE', 'CLASS']:
                continue
            if isinstance(value, SymConfConfig):
                filtered[key] = value._to_dict()
            else:
                filtered[key] = value
        return filtered
    
    def realize(self, overwrites: Optional[Dict[str, Any]] = None) -> Any:
        """Realize object(s) from configuration.
        
        Args:
            overwrites: Optional parameter overwrites using dot notation
            
        Returns:
            Realized object or updated configuration
        """
        if 'TYPE' not in self.__dict__:
            # No TYPE, just return SymConfConfig with realized children
            result = {}
            for key, value in self.__dict__.items():
                if isinstance(value, SymConfConfig):
                    result[key] = value.realize(overwrites)
                else:
                    result[key] = value
            return SymConfConfig(result)
        
        # Apply overwrites if provided
        config_data = self._to_dict()
        if overwrites:
            config_data = self._apply_overwrites(config_data, overwrites)
        
        return self._realize_single_object(config_data)
    
    def pretty(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Serialize configuration to flattened format.
        
        Args:
            exclude: List of parameter paths to exclude
            
        Returns:
            Flattened configuration dictionary
        """
        exclude = exclude or []
        result = {}
        
        def _flatten(data: Dict[str, Any], prefix: str = "") -> None:
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                if full_key in exclude:
                    continue
                
                if isinstance(value, SymConfConfig):
                    _flatten(value._to_dict(), full_key)
                elif isinstance(value, dict):
                    _flatten(value, full_key)
                else:
                    # Convert objects back to their type string if possible
                    if hasattr(value, '__class__') and hasattr(value.__class__, '__module__'):
                        if value.__class__.__module__ != 'builtins':
                            class_name = f"{value.__class__.__module__}.{value.__class__.__name__}"
                            result[full_key] = class_name
                        else:
                            result[full_key] = value
                    else:
                        result[full_key] = value
        
        _flatten(self._to_dict())
        return result

    def _apply_overwrites(self, data: Dict[str, Any], overwrites: Dict[str, Any]) -> Dict[str, Any]:
        """Apply overwrites using dot notation.
        
        Args:
            data: Original configuration data
            overwrites: Overwrites with dot notation keys
            
        Returns:
            Updated configuration data
        """
        result = copy.deepcopy(data)
        for key_path, value in overwrites.items():
            self._set_nested_value(result, key_path, value)
        return result
    
    def _set_nested_value(self, data: Dict[str, Any], key_path: str, value: Any) -> None:
        """Set nested value using dot notation.
        
        Args:
            data: Dictionary to modify
            key_path: Dot-separated key path
            value: Value to set
        """
        keys = key_path.split('.')
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def _realize_single_object(self, config_data: Dict[str, Any]) -> Any:
        """Realize a single object from configuration.
        
        Args:
            config_data: Configuration data dictionary
            
        Returns:
            Realized object
        """
        type_path = config_data['TYPE']
        
        try:
            obj = import_object(type_path)
        except Exception as e:
            raise ImportError(f"Failed to import {type_path}: {e}")
        
        # Handle different object types
        if '.' in type_path and 'CLASS' in config_data:
            # Instance method
            class_path = '.'.join(type_path.split('.')[:-1])
            method_name = type_path.split('.')[-1]
            
            class_obj = import_object(class_path)
            instance = class_obj(**config_data['CLASS'])
            method = getattr(instance, method_name)
            
            # Get method kwargs
            kwargs = {k: v for k, v in config_data.items() if k not in ['TYPE', 'CLASS']}
            
            # Realize nested objects in kwargs
            for key, value in kwargs.items():
                if isinstance(value, dict) and 'TYPE' in value:
                    kwargs[key] = self._realize_single_object(value)
            
            return method(**kwargs)
        
        # Regular class/function instantiation
        kwargs = {k: v for k, v in config_data.items() if k not in ['TYPE', 'CLASS']}
        
        # Realize nested objects in kwargs (depth-first)
        for key, value in kwargs.items():
            if isinstance(value, dict) and 'TYPE' in value:
                kwargs[key] = self._realize_single_object(value)
        
        return obj(**kwargs)
    
    
    
    def _to_dict(self) -> Dict[str, Any]:
        """Convert to plain dictionary.
        
        Returns:
            Plain dictionary representation
        """
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, SymConfConfig):
                result[key] = value._to_dict()
            elif isinstance(value, list):
                result[key] = [
                    item._to_dict() if isinstance(item, SymConfConfig) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    def __repr__(self) -> str:
        """String representation."""
        return f"SymConfConfig({self._to_dict()})"