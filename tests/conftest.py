"""Pytest configuration and shared fixtures for SymConf tests."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator

import pytest
import yaml

from symconf import SymConfParser


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def parser() -> SymConfParser:
    """Create a basic SymConfParser instance."""
    return SymConfParser()


@pytest.fixture
def parser_with_validation() -> SymConfParser:
    """Create a SymConfParser with validation enabled."""
    return SymConfParser(validate_type=True, validate_mapping=True)


@pytest.fixture
def parser_without_validation() -> SymConfParser:
    """Create a SymConfParser with validation disabled."""
    return SymConfParser(validate_type=False, validate_mapping=False)


def write_yaml_file(file_path: Path, data: Dict[str, Any]) -> None:
    """Write data to YAML file.

    Args:
        file_path: Path to write file
        data: Data to write
    """
    with open(file_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def set_env_vars(**env_vars: str) -> None:
    """Set environment variables.

    Args:
        **env_vars: Environment variables to set
    """
    for key, value in env_vars.items():
        os.environ[key] = value


def cleanup_env_vars(*var_names: str) -> None:
    """Clean up environment variables.

    Args:
        *var_names: Variable names to remove
    """
    for var_name in var_names:
        os.environ.pop(var_name, None)
