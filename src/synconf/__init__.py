"""SynConf - Symbolic Configuration Management System.

A comprehensive configuration management system supporting multi-source loading,
variable interpolation, object realization, and parameter validation.
"""
# ruff: noqa: F401

from .config import SynConfig
from .exceptions import (
    CircularInterpolationError,
    ParameterValidationError,
    SynConfError,
)
from .parameter_tracer import ParameterChainTracer
from .parser import SynConfParser

__version__ = "0.1.0"
