"""TwinConf: An entanglement of configuration and code."""

from .config import ConfigurationObject
from .parser import TwinConfParser

__version__ = "0.1.0"
__all__ = ["TwinConfParser", "ConfigurationObject"]


def main() -> None:
    """Main entry point for the twinconf CLI."""
    pass
