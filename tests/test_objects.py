"""Test objects for SymConf testing."""

from typing import Union, Literal, Optional


class Optimizer:
    """Test optimizer class."""

    def __init__(self, lr: float):
        """Initialize optimizer.

        Args:
            lr: Learning rate
        """
        self.lr = lr

    def __repr__(self):
        return f"Optimizer(lr={self.lr})"


class AwesomeModel:
    """Test model class."""

    def __init__(self, learning_rate: float = 1e-4, hidden_size: int = 32, optimizer: Optional[Optimizer] = None):
        """Initialize model.

        Args:
            learning_rate: Learning rate for the model
            hidden_size: Hidden layer size
            optimizer: Optional optimizer instance
        """
        self.learning_rate = learning_rate
        self.hidden_size = hidden_size
        self.optimizer = optimizer

    def __repr__(self):
        return f"AwesomeModel(learning_rate={self.learning_rate}, hidden_size={self.hidden_size}, optimizer={self.optimizer})"


def create_optimizer(lr: float) -> Optimizer:
    """Factory function for creating optimizers.

    Args:
        lr: Learning rate

    Returns:
        Optimizer instance
    """
    return Optimizer(lr)


class Parent:
    """Test parent class for validation."""

    def __init__(
        self,
        name: str,
        number: Union[int, float, None] = None,
        vocab: Union[None, list[float]] = None,
        toy: Union[str, None] = None,
    ):
        """Initialize parent.

        Args:
            name: Name parameter
            number: Numeric parameter
            vocab: Vocabulary list
            toy: Toy parameter
        """
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
        dummy=3,  # No type annotation
        name: Optional[str] = None,
        **kwargs,
    ):
        """Initialize child.

        Args:
            percent: Percentage value
            animal: Animal type
            dummy: Dummy parameter without type annotation
            name: Optional name
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(name=name or "John", **kwargs)
        self.percent = percent
        self.animal = animal
        self.dummy = dummy


class Experiment:
    """Test experiment class for instance methods."""

    def __init__(self, seed: int):
        """Initialize experiment.

        Args:
            seed: Random seed
        """
        self.seed = seed

    def cross_validate(self, folds: int) -> dict[str, float]:
        """Perform cross validation.

        Args:
            folds: Number of folds

        Returns:
            Validation metrics
        """
        return {"F1": 0.9, "Precision": 0.95}


def square(value: float) -> float:
    """Square a value.

    Args:
        value: Input value

    Returns:
        Squared value
    """
    return value * value


class TestModel:
    """Simple test model for type validation."""

    def __init__(self, learning_rate: float = 1e-4, batch_size: int = 32, activation: str = "relu"):
        """Initialize test model.

        Args:
            learning_rate: Learning rate
            batch_size: Batch size
            activation: Activation function
        """
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.activation = activation


# Define the complex kwargs tracing chain as shown in HOWTO.md
class BClass:
    """Test class B for kwargs tracing."""

    def my_method(self, g: float):
        """Method with parameter g.

        Args:
            g: 猩猩 parameter
        """
        self.g = g


def func(f: int = 5, **kwargs):
    """Function for kwargs tracing.

    Args:
        f: 狐狸 parameter
        **kwargs: Additional kwargs
    """
    b = BClass()
    b.my_method(**kwargs)


class AClass:
    """Test class A for kwargs tracing."""

    @classmethod
    def create(cls, e, **kwargs) -> "AClass":
        """Factory method.

        Args:
            e: Elephant parameter
            **kwargs: Additional kwargs
        """
        func(**kwargs)
        return cls()


class ParentClass:
    """Parent class for kwargs tracing."""

    def __init__(self, a, b: bool, c, **kwargs):
        """Initialize parent.

        Args:
            a: Alpha parameter
            b: Beta parameter
            c: Gamma parameter
            **kwargs: Additional kwargs
        """
        AClass.create(**kwargs)
        self.a = a
        self.b = b
        self.c = c


class ChildClass(ParentClass):
    """Child class for comprehensive kwargs tracing testing."""

    def __init__(self, percent: float, animal: Literal["cat", "dog"] = "dog", **kwargs):
        """Initialize child.

        Args:
            percent: Percentage parameter
            animal: Animal parameter
            **kwargs: Additional kwargs passed to parent
        """
        super().__init__(a=3, c=percent * 5, **kwargs)
        self.percent = percent
        self.animal = animal
