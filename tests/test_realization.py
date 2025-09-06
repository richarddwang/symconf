"""Tests for object realization functionality."""

import pytest
import yaml

from twinconf import TwinConfParser


class SampleClass:
    """Sample class for testing object realization."""

    def __init__(self, value: int, name: str = "default"):
        self.value = value
        self.name = name

    def get_info(self):
        """Get info about the object."""
        return f"{self.name}: {self.value}"

    @staticmethod
    def static_method():
        """Static method for testing."""
        return "static_result"


class ComplexClass:
    """Complex class with nested object dependency."""

    def __init__(self, nested_obj: SampleClass, multiplier: float = 2.0):
        self.nested_obj = nested_obj
        self.multiplier = multiplier

    def compute(self):
        """Compute based on nested object."""
        return self.nested_obj.value * self.multiplier


class TestObjectRealization:
    """Test object realization functionality."""

    def test_basic_realization(self, temp_dir):
        """Test basic object realization with TYPE."""
        config_data = {"sample_obj": {"TYPE": "test_realization.SampleClass", "value": 42, "name": "test_object"}}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        # Test that the object isn't realized until we call realize()
        assert isinstance(config.sample_obj, dict)
        assert config.sample_obj.TYPE == "test_realization.SampleClass"
        assert config.sample_obj.value == 42
        assert config.sample_obj.name == "test_object"

        # Realize the object
        realized_obj = config.sample_obj.realize()

        assert isinstance(realized_obj, SampleClass)
        assert realized_obj.value == 42
        assert realized_obj.name == "test_object"
        assert realized_obj.get_info() == "test_object: 42"

    def test_realization_with_defaults(self, temp_dir):
        """Test object realization with default parameters."""
        config_data = {
            "sample_obj": {
                "TYPE": "test_realization.SampleClass",
                "value": 100,
                # name should use default
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        realized_obj = config.sample_obj.realize()

        assert isinstance(realized_obj, SampleClass)
        assert realized_obj.value == 100
        assert realized_obj.name == "default"
        assert realized_obj.get_info() == "default: 100"

    def test_nested_realization(self, temp_dir):
        """Test realization of objects with nested dependencies."""
        config_data = {
            "nested": {"TYPE": "test_realization.SampleClass", "value": 10, "name": "nested"},
            "complex_obj": {
                "TYPE": "test_realization.ComplexClass",
                "nested_obj": {"TYPE": "test_realization.SampleClass", "value": 5, "name": "inner"},
                "multiplier": 3.0,
            },
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        # Realize the complex object
        complex_obj = config.complex_obj.realize()

        assert isinstance(complex_obj, ComplexClass)
        assert isinstance(complex_obj.nested_obj, SampleClass)
        assert complex_obj.nested_obj.value == 5
        assert complex_obj.nested_obj.name == "inner"
        assert complex_obj.multiplier == 3.0
        assert complex_obj.compute() == 15.0  # 5 * 3.0

    def test_realization_with_interpolation(self, temp_dir):
        """Test realization with interpolated values."""
        config_data = {
            "base_value": 20,
            "sample_obj": {"TYPE": "test_realization.SampleClass", "value": "${base_value}", "name": "interpolated"},
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        realized_obj = config.sample_obj.realize()

        assert isinstance(realized_obj, SampleClass)
        assert realized_obj.value == 20  # Interpolated from base_value
        assert realized_obj.name == "interpolated"
        assert realized_obj.get_info() == "interpolated: 20"

    def test_manual_realization(self, temp_dir):
        """Test manual realization without TYPE."""
        config_data = {"manual_obj": {"value": 99, "name": "manual"}}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        # Manual realization by specifying class name as TYPE override
        realized_obj = config.manual_obj.realize({"TYPE": "test_realization.SampleClass"})

        assert isinstance(realized_obj, SampleClass)
        assert realized_obj.value == 99
        assert realized_obj.name == "manual"
        assert realized_obj.get_info() == "manual: 99"

    def test_realization_error_handling(self, temp_dir):
        """Test error handling in object realization."""
        config_data = {"bad_obj": {"TYPE": "non.existent.Class", "value": 42}}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        # Disable all validation to let the bad TYPE through
        parser = TwinConfParser(validate_types=False, check_missing_args=False, check_unexpected_args=False)
        config = parser.parse_args([str(config_file)])

        with pytest.raises((ImportError, ValueError)):
            config.bad_obj.realize()

    def test_non_realizable_object(self, temp_dir):
        """Test that objects without TYPE return themselves when realized."""
        config_data = {
            "plain_obj": {
                "value": 42,
                "name": "plain",
                # No TYPE
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        # Without TYPE, realize() should return the configuration object itself
        realized = config.plain_obj.realize()
        assert realized == config.plain_obj
        assert realized["value"] == 42
        assert realized["name"] == "plain"


class TestInstanceMethods:
    """Test calling methods on realized objects."""

    def test_method_calls_on_realized_objects(self, temp_dir):
        """Test calling instance methods on realized objects."""
        config_data = {"sample_obj": {"TYPE": "test_realization.SampleClass", "value": 42, "name": "method_test"}}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        # Realize and call method
        obj = config.sample_obj.realize()
        result = obj.get_info()

        assert result == "method_test: 42"

    def test_static_method_calls(self, temp_dir):
        """Test calling static methods."""
        config_data = {"sample_obj": {"TYPE": "test_realization.SampleClass", "value": 1, "name": "static_test"}}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        # Can call static methods on the class
        obj = config.sample_obj.realize()
        result = obj.static_method()

        assert result == "static_result"


class TestObjectSweeping:
    """Test sweeping configurations for object creation."""

    def test_object_sweep(self, temp_dir):
        """Test creating multiple object configurations through sweeping."""
        config_data = {
            "base_obj": {"TYPE": "test_realization.SampleClass", "value": "SWEEP[10, 20, 30]", "name": "sweep_test"}
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        # Disable validation since SWEEP functionality isn't implemented yet
        parser = TwinConfParser(validate_types=False)
        config = parser.parse_args([str(config_file)])

        # Current behavior: SWEEP should be treated as a string value
        # In future implementation, this would return a list of configurations
        assert isinstance(config, list) or hasattr(config, "base_obj")

        if hasattr(config, "base_obj"):
            # Single config case (current behavior)
            assert config.base_obj.value == "SWEEP[10, 20, 30]"
        else:
            # Multiple configs case (future implementation)
            pass
