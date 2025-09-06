"""Utility functions for TwinConf."""

from typing import Any, Dict, List


def process_list_type(config: Dict[str, Any]) -> List[Any]:
    """Process LIST type configurations into actual lists.

    Args:
        config: Configuration dictionary with TYPE: LIST

    Returns:
        List of values from the configuration
    """
    result = []
    for key, value in config.items():
        if key == "TYPE":
            continue
        if value == "DELETE":
            continue  # Skip deleted items
        result.append(value)

    return result


def apply_list_merges(base_config: Dict[str, Any], merge_config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply LIST-specific merges.

    Args:
        base_config: Base configuration
        merge_config: Configuration to merge

    Returns:
        Merged configuration
    """
    if base_config.get("TYPE") == "LIST" and merge_config.get("TYPE") == "LIST":
        # Merge LIST configurations
        result = {"TYPE": "LIST"}

        # Start with base config items
        for key, value in base_config.items():
            if key != "TYPE":
                result[key] = value

        # Apply merge config items
        for key, value in merge_config.items():
            if key != "TYPE":
                result[key] = value

        return result

    return merge_config  # Default deep merge behavior
