from typing import Literal


class BClass:
    def my_method(self, g: float):
        """
        Args:
            g: 猩猩
        """


def func(f: int = 5, **kwargs):
    """
    Args:
        f(int, optional): 狐狸。
    """
    b = BClass()
    b.my_method(**kwargs)


class AClass:
    @classmethod
    def create(cls, e="hi", **kwargs) -> "AClass":
        func(**kwargs)
        ...


class Parent:
    def __init__(self, a, b: Literal["cat", "dog"], c, **kwargs):
        AClass.create(**kwargs)


class Child(Parent):
    def __init__(self, d, **kwargs):
        super().__init__(a=3, c=d * 5, **kwargs)
