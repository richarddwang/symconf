"""Classes for testing parameter mapping validation.

Following HOWTO.md structure for Step 6 parameter mapping validation test.
"""


class Parent:
    """Test parent class for parameter mapping validation."""

    def __init__(self, c: int, d: float):
        """Initialize parent for mapping test.

        Args:
            c: Parameter c
            d: Parameter d
        """
        self.c = c
        self.d = d


class Child(Parent):
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


def func(x: int):
    """Test function for parameter mapping validation."""
    pass
