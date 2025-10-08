"""Pytest configuration and shared fixtures for SymConf tests."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, Literal, Optional, Type, Union

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


# Test classes for validation tests
class Toy: ...


class SuperToy(Toy): ...


class Parent:
    def __init__(
        self,
        name: str,
        number: int | float | None = None,
        vocab: None | list[float] = None,
        toy: Union[str, None] = None,
    ):
        self.name = name
        self.number = number
        self.vocab = vocab
        self.toy = toy


class Child(Parent):
    """Test child class for validation."""

    def __init__(
        self,
        percent: float,
        animal: Literal["cat", "dog"] = "dog",
        dummy=3,
        name: Optional[str] = None,
        toy: Optional[Toy] = None,
        stoy: Optional[SuperToy] = None,
        toy_cls: Optional[Type[Toy]] = None,
        stoy_cls: Optional[Type[SuperToy]] = None,
        **kwargs,
    ):
        super().__init__(name=name or "John", **kwargs)
        self.percent = percent
        self.animal = animal
        self.dummy = dummy
        self.toy = toy
        self.stoy = stoy
        self.toy_cls = toy_cls
        self.stoy_cls = stoy_cls


class AwesomeModel:
    """Test model class for object realization."""

    def __init__(self, learning_rate: float = 1e-4, batch_size: int = 32):
        """Initialize awesome model.

        Args:
            learning_rate: Learning rate parameter
            batch_size: Batch size parameter
        """
        self.learning_rate = learning_rate
        self.batch_size = batch_size


class Optimizer:
    """Test optimizer class."""

    def __init__(self, lr: float):
        """Initialize optimizer.

        Args:
            lr: Learning rate
        """
        self.lr = lr


class AwesomeModelWithOptimizer:
    """Test model class with optimizer dependency."""

    def __init__(self, hidden_size: int, optimizer: Optimizer):
        """Initialize model with optimizer.

        Args:
            hidden_size: Hidden layer size
            optimizer: Optimizer instance
        """
        self.hidden_size = hidden_size
        self.optimizer = optimizer


def create_optimizer(lr: float) -> Optimizer:
    """Create optimizer instance.

    Args:
        lr: Learning rate

    Returns:
        Optimizer instance
    """
    return Optimizer(lr)


def func(act: str, message: str = "hello"):
    pass


class BaseModel:
    """Test base model class for Step 4 default completion example."""

    def __init__(self, learning_rate: float = 1e-4, batch_size: int = 32, **kwargs):
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        func(**kwargs)


class AwesomeModelStep4(BaseModel):
    def __init__(self, loss_scale: float = 1.0, **kwargs):
        self.loss_scale = loss_scale
        super().__init__(batch_size=16, **kwargs)


def square(value: float) -> float:
    """Square a value.

    Args:
        value: Input value

    Returns:
        Squared value
    """
    return value * value


class Experiment:
    """Test experiment class for instance method testing."""

    def __init__(self, seed: int):
        """Initialize experiment.

        Args:
            seed: Random seed
        """
        self.seed = seed

    def cross_validate(self, folds: int) -> Dict[str, float]:
        """Perform cross validation.

        Args:
            folds: Number of folds

        Returns:
            Validation metrics
        """
        return {"F1": 0.9, "Precision": 0.95}


@pytest.fixture
def test_classes() -> Dict[str, Type]:
    """Provide test classes for validation tests."""
    return {
        "Parent": Parent,
        "Child": Child,
        "Toy": Toy,
        "SuperToy": SuperToy,
        "AwesomeModel": AwesomeModel,
        "Optimizer": Optimizer,
        "AwesomeModelWithOptimizer": AwesomeModelWithOptimizer,
        "Experiment": Experiment,
        "BaseModel": BaseModel,
        "AwesomeModelStep4": AwesomeModelStep4,
        "ParentForMapping": ParentForMapping,
        "ChildForMapping": ChildForMapping,
    }


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


# Additional classes for kwargs chain testing from HOWTO.md
class BClass:
    """Test B class for kwargs chain testing."""

    def my_method(self, g: float):
        """Test method.

        Args:
            g: 猩猩
        """
        pass


def func_with_kwargs(f: int = 5, **kwargs):
    """Test function with kwargs.

    Args:
        f: 狐狸
        **kwargs: Additional arguments passed to BClass.my_method
    """
    b = BClass()
    b.my_method(**kwargs)


class AClass:
    """Test A class for kwargs chain testing."""

    @classmethod
    def create(cls, e, **kwargs) -> "AClass":
        """Create AClass instance.

        Args:
            e: Parameter e
            **kwargs: Additional arguments passed to func
        """
        func_with_kwargs(**kwargs)
        return cls()


class ParentForKwargs:
    """Test parent class for kwargs chain testing."""

    def __init__(self, a, b: bool, c, **kwargs):
        """Initialize parent.

        Args:
            a: Parameter a
            b: Parameter b
            c: Parameter c
            **kwargs: Additional arguments passed to AClass.create
        """
        AClass.create(**kwargs)


class ChildForKwargs(ParentForKwargs):
    """Test child class for kwargs chain testing."""

    def __init__(self, d, **kwargs):
        """Initialize child.

        Args:
            d: Parameter d
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(a=3, c=d * 5, **kwargs)


# Additional classes for Step 6 parameter mapping validation test
# Following HOWTO.md structure
class ParentForMapping:
    """Test parent class for parameter mapping validation."""

    def __init__(self, c: int, d: float):
        """Initialize parent for mapping test.

        Args:
            c: Parameter c
            d: Parameter d
        """
        self.c = c
        self.d = d


class ChildForMapping(ParentForMapping):
    """Test child class for parameter mapping validation."""

    def __init__(self, a: int, b: int = 3, **kwargs):
        """Initialize child for mapping test.

        Args:
            a: Parameter a (required)
            b: Parameter b (optional, default=3)
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(c=a + b, **kwargs)
        self.a = a
        self.b = b
