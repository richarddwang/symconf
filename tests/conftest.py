"""Pytest configuration and shared fixtures for SynConf tests."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator

import pytest
import yaml
from synconf import SynConfParser


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def parser() -> SynConfParser:
    """Create a basic SynConfParser instance."""
    return SynConfParser()


@pytest.fixture
def parser_with_validation() -> SynConfParser:
    """Create a SynConfParser with validation enabled."""
    return SynConfParser(validate_type=True, validate_mapping=True)


@pytest.fixture
def parser_without_validation() -> SynConfParser:
    """Create a SynConfParser with validation disabled."""
    return SynConfParser(validate_type=False, validate_mapping=False)


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
