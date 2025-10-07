"""Utility functions for SymConf."""

import importlib
import os
from copy import deepcopy
from typing import Any, Dict


def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with update taking precedence.

    Args:
        base: Base dictionary
        update: Update dictionary (takes precedence)

    Returns:
        Merged dictionary
    """
    result = deepcopy(base)
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def import_object(path: str) -> Any:
    """Import an object by its module path.

    Args:
        path: Import path like 'module.submodule.ClassName'

    Returns:
        Imported object

    Raises:
        ImportError: If object cannot be imported
    """
    if "." not in path:
        # Handle built-in objects
        try:
            return eval(path)
        except NameError:
            raise ImportError(f"Cannot import {path}")

    # Split into module and object parts
    parts = path.split(".")
    module_path = ".".join(parts[:-1])
    object_name = parts[-1]

    try:
        module = importlib.import_module(module_path)
        return getattr(module, object_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Cannot import {path}: {e}")


def load_dotenv(file_path: str) -> Dict[str, str]:
    """Load environment variables from a dotenv file.

    Args:
        file_path: Path to the dotenv file

    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    if not os.path.exists(file_path):
        return env_vars

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


def remove_parameters(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove parameters marked with REMOVE keyword.

    Args:
        data: Configuration data

    Returns:
        Configuration with REMOVE parameters filtered out
    """
    result = {}
    for key, value in data.items():
        if value == "REMOVE":
            continue
        elif isinstance(value, dict):
            cleaned = remove_parameters(value)
            if cleaned:  # Only include non-empty dicts
                result[key] = cleaned
        else:
            result[key] = value

    return result


def process_list_type(data: Dict[str, Any]) -> Any:
    """Process LIST type configurations.

    Args:
        data: Configuration data that might contain LIST types

    Returns:
        Processed configuration with LIST types converted to lists
    """
    if isinstance(data, dict):
        if data.get("TYPE") == "LIST":
            # Convert to list, excluding TYPE and REMOVE values
            items = []
            for key, value in data.items():
                if key == "TYPE":
                    continue
                items.append(value)
            return items
        else:
            # Recursively process nested structures
            result = {}
            for key, value in data.items():
                result[key] = process_list_type(value)
            return result
    elif isinstance(data, list):
        return [process_list_type(item) for item in data]
    else:
        return data
