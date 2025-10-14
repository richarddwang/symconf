"""Basic validation test classes."""

from typing import Literal, Optional, Type, Union


class Toy:
    """Basic toy class for testing."""

    pass


class SuperToy(Toy):
    """Enhanced toy class inheriting from Toy."""

    pass


class Parent:
    """Parent class for validation testing."""

    def __init__(
        self,
        name: str,
        number: int | float | None = None,
        vocab: None | list[float] = None,
        toy: Union[str, None] = None,
    ): ...


class Child(Parent):
    """Test child class for validation."""

    def __init__(
        self,
        percent: float,
        animal: Literal["cat", "dog"] = "dog",
        precision: Literal[64, 32, 16] | Literal["16-true", "bf16"] | None = None,
        dummy=3,
        name: Optional[str] = None,
        toy: Optional[Toy] = None,
        stoy: Optional[SuperToy] = None,
        toy_cls: Optional[Type[Toy]] = None,
        stoy_cls: Type[SuperToy] = SuperToy,
        **kwargs,
    ):
        super().__init__(name=name or "John", **kwargs)
