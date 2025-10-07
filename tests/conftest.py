"""Conftest file for SymConf tests."""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for test configuration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_config_files(temp_config_dir):
    """Create sample configuration files for testing."""
    config1 = temp_config_dir / "config1.yaml"
    config1.write_text("""
server: 
  host: localhost
  ports: 
    - 8080
    - 8081
""")

    config2 = temp_config_dir / "config2.yaml"
    config2.write_text("""
server:
  timeout: 10
  ports:
    - 9090
""")

    return {"config1": config1, "config2": config2}


@pytest.fixture
def sample_env_file(temp_config_dir):
    """Create sample environment file for testing."""
    env_file = temp_config_dir / "test.env"
    env_file.write_text("""
BASE_FEATURE_SIZE=10
FEATURE_SIZE=64
""")
    return env_file


@pytest.fixture
def interpolation_config(temp_config_dir):
    """Create configuration file with interpolation examples."""
    config = temp_config_dir / "interpolation.yaml"
    config.write_text("""
dataset:
  name: cifar10
  num_classes: ${BASE_FEATURE_SIZE}

model:
  output_features: ${dataset.num_classes}
  name: model_${dataset.name}_v2
  hidden_dim: ${FEATURE_SIZE}
  dropout: ${0.1 if 10 < 5 else 0.0}

total_params: ${10 + 10}
""")
    return config


@pytest.fixture
def object_config(temp_config_dir):
    """Create configuration file with object definitions."""
    config = temp_config_dir / "objects.yaml"
    config.write_text("""
model:
  TYPE: tests.test_objects.AwesomeModel
  learning_rate: 1e-3
  hidden_size: 64
  optimizer:
    TYPE: tests.test_objects.create_optimizer
    lr: 0.01

experiment:
  TYPE: tests.test_objects.Experiment.cross_validate
  folds: 5
  CLASS:
    seed: 1
""")
    return config


@pytest.fixture
def list_config(temp_config_dir):
    """Create configuration files for LIST type testing."""
    default_config = temp_config_dir / "default_callbacks.yaml"
    default_config.write_text("""
callbacks:
  TYPE: LIST
  log: log_callback
  ckpt: save_model_callback
  debug: debug_callback
""")

    override_config = temp_config_dir / "override_callbacks.yaml"
    override_config.write_text("""
callbacks:
  TYPE: LIST
  ckpt: REMOVE
  stop: early_stopping_callback
""")

    return {"default": default_config, "override": override_config}


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    original_env = dict(os.environ)

    # Set test environment variables
    os.environ.update({"BASE_FEATURE_SIZE": "10", "FEATURE_SIZE": "64", "TEST_VAR": "test_value"})

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
