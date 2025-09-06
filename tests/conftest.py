"""Test configuration and fixtures for TwinConf tests."""

import tempfile
from pathlib import Path
from typing import Dict

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_yaml_content():
    """Sample YAML content for testing."""
    return {
        "server": {"host": "localhost", "ports": [8080, 8081], "timeout": 10},
        "database": {"url": "sqlite:///:memory:", "pool_size": 5},
    }


@pytest.fixture
def sample_config_file(temp_dir, sample_yaml_content):
    """Create a sample configuration file."""
    import yaml

    config_file = temp_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(sample_yaml_content, f)
    return config_file


@pytest.fixture
def sample_dotenv_file(temp_dir):
    """Create a sample dotenv file."""
    env_file = temp_dir / ".env"
    with open(env_file, "w") as f:
        f.write("DATABASE_URL=postgresql://localhost/test\n")
        f.write("DEBUG=true\n")
        f.write("PORT=9000\n")
    return env_file


# Sample classes for testing object realization
class TestModel:
    def __init__(self, hidden_size: int, learning_rate: float = 0.01, dropout: float = 0.1):
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self.dropout = dropout


class TestOptimizer:
    def __init__(self, lr: float, weight_decay: float = 0.0):
        self.lr = lr
        self.weight_decay = weight_decay


def create_optimizer(lr: float, optimizer_type: str = "adam") -> TestOptimizer:
    """Factory function for creating optimizers."""
    return TestOptimizer(lr=lr)


class TestExperiment:
    def __init__(self, seed: int, name: str = "test"):
        self.seed = seed
        self.name = name

    def cross_validate(self, folds: int, metric: str = "accuracy") -> Dict[str, float]:
        """Sample instance method."""
        return {"accuracy": 0.95, "f1": 0.93}


def sample_sweep_function():
    """Sample sweep function for testing."""
    for lr in [0.01, 0.1]:
        for batch_size in [16, 32]:
            if lr == 0.01 and batch_size == 16:
                continue
            yield {"model.learning_rate": lr, "training.batch_size": batch_size}
