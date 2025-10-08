"""SymConf - Symbolic Configuration Management System.

A comprehensive configuration management system supporting multi-source loading,
variable interpolation, object realization, and parameter validation.
"""
# ruff: noqa: F401

from .config import SymConfConfig
from .exceptions import (
    CircularInterpolationError,
    ParameterValidationError,
    SymConfError,
)
from .parameter_tracer import ParameterChainTracer
from .parser import SymConfParser

__version__ = "0.1.0"
