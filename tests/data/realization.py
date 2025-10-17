"""Model classes for object realization testing."""

from typing import Any, Dict


class Optimizer:
    """Test optimizer class."""

    def __init__(self, lr: float):
        """Initialize optimizer.

        Args:
            lr: Learning rate
        """
        self.lr = lr


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
    """Basic function for testing."""
    pass


class BaseModel:
    """Test base model class for Step 4 default completion example."""

    def __init__(self, learning_rate: float = 1e-4, batch_size: int = 32, **kwargs):
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        func(**kwargs)


class AwesomeModelStep4(BaseModel):
    """Enhanced model with loss scale parameter."""

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

    def __init__(self, seed: int = 0):
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


class DataProcessor:
    """Test class for manual instance method realization."""

    def __init__(self, complex_data: Any):
        """Initialize data processor.

        Args:
            complex_data: Complex data input
        """
        self.num_classes = 3
        self.complex_data = complex_data

    def get_num_targets(self, batch_size: int) -> int:
        """Get number of targets for batch.

        Args:
            batch_size: Size of the batch

        Returns:
            Total number of targets
        """
        return self.num_classes * batch_size
