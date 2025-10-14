"""Utility functions for SynConf."""

import importlib
import re
from copy import deepcopy
from typing import Any, Callable, Dict, Type

import yaml

OBJECT_TYPE = Callable | Type[Any]


def load_yaml(stream: Any) -> Any:
    """Load YAML content from a stream.

    Args:
        stream: Stream to read YAML from  # (file-like object or string)
    Returns:
        Parsed YAML content as a dictionary  # (nested dict structure)
    """
    # Use UnsafeLoader to allow python-related tags
    loader = yaml.UnsafeLoader

    # Custom loader to handle scientific notation correctly
    loader.add_implicit_resolver(
        tag="tag:yaml.org,2002:float",
        regexp=re.compile(r"-? [1-9] ( \. [0-9]* [1-9] )? ( e [-+] [1-9] [0-9]* )?", re.X),
        first=list("-+0123456789."),
    )

    return yaml.load(stream, Loader=loader)


def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with update taking precedence.

    Args:
        base: Base dictionary  # (original configuration)
        update: Update dictionary (takes precedence)  # (overrides and additions)

    Returns:
        Merged dictionary  # (combined configuration with deep merging)
    """
    result = deepcopy(base)

    # Merge each key from update into result
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Replace or add the value
            result[key] = deepcopy(value)
    return result


def import_object(path: str) -> OBJECT_TYPE:
    """Import an object by its module path.

    Args:
        path: Import path like 'module.submodule.ClassName' or 'module.ClassName.method'

    Returns:
        Imported object  # (class, function, or other importable object)

    Raises:
        ImportError: If object cannot be imported
    """
    # Handle simple names without dots (built-in objects)
    if "." not in path:
        # Handle built-in objects
        try:
            return eval(path)
        except NameError:
            raise ImportError(f"Cannot import {path}")

    # Try to import progressively from longest to shortest module path
    parts = path.split(".")  # List[str] (path components)

    # Start from the full path and work backwards
    for i in range(len(parts) - 1, 0, -1):
        module_path = ".".join(parts[:i])  # Module path to try
        remaining_parts = parts[i:]  # Remaining attribute path

        try:
            # Import the module
            module = importlib.import_module(module_path)

            # Navigate through the remaining parts (classes, methods, etc.)
            obj = module
            for part in remaining_parts:
                obj = getattr(obj, part)

            return obj
        except (ImportError, AttributeError):
            # Try shorter module path
            continue

    # If all attempts failed, raise ImportError
    raise ImportError(f"Cannot import {path}")


def get_method_class(method: Callable) -> Type:
    """Get the class that defines a given method.

    Args:
        method: Method to inspect

    Returns:
        Class that defines the method

    Raises:
        ValueError: If method is not bound to a class
    """
    if hasattr(method, "__self__"):
        return method.__self__.__class__
    else:
        module = importlib.import_module(method.__module__)
        class_name = method.__qualname__.split(".")[0]
        return getattr(module, class_name)


def remove_parameters(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove parameters marked with REMOVE keyword.

    Args:
        data: Configuration data  # (nested dict with potential REMOVE markers)

    Returns:
        Configuration with REMOVE parameters filtered out  # (cleaned configuration)
    """
    result = {}  # Dict[str, Any] (cleaned configuration)

    # Process each key-value pair
    for key, value in data.items():
        if value == "REMOVE":
            # Skip parameters marked for removal
            continue
        elif isinstance(value, dict):
            # Recursively clean nested dictionaries
            cleaned = remove_parameters(value)
            if cleaned:  # Only include non-empty dicts
                result[key] = cleaned
        else:
            # Keep regular values
            result[key] = value

    return result


def process_list_type(data: Dict[str, Any]) -> Any:
    """Process LIST type configurations.

    Args:
        data: Configuration data that might contain LIST types  # (nested dict with LIST markers)

    Returns:
        Processed configuration with LIST types converted to lists  # (converted structure)
    """
    # Handle dictionary structures
    if isinstance(data, dict):
        if data.get("TYPE") == "LIST":
            # Convert to list, excluding TYPE and REMOVE values
            items = []  # List[Any] (collected list items)
            for key, value in data.items():
                if key == "TYPE":
                    continue  # Skip TYPE marker
                items.append(value)
            return items
        else:
            # Recursively process nested structures
            result = {}  # Dict[str, Any] (processed nested structure)
            for key, value in data.items():
                result[key] = process_list_type(value)
            return result
    # Handle list structures
    elif isinstance(data, list):
        return [process_list_type(item) for item in data]
    else:
        # Return primitive values as-is
        return data
