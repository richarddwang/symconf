"""SymConf - Symbolic Configuration Management System.

A comprehensive configuration management system supporting multi-source loading,
variable interpolation, object realization, and parameter validation.
"""

from .parser import SymConfParser  # ruff: noqa: F401
from .config import SymConfConfig  # ruff: noqa: F401
from .exceptions import (  # ruff: noqa: F401
    SymConfError,
    CircularInterpolationError,
    ParameterValidationError,
)

__version__ = "0.1.0"
