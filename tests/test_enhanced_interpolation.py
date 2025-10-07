"""Tests for enhanced InterpolationEngine with improved _get_nested_value method."""

import os

import pytest

from symconf.exceptions import CircularInterpolationError
from symconf.utils import InterpolationEngine


class TestEnhancedInterpolationEngine:
    """Test the enhanced InterpolationEngine with improved _get_nested_value method."""

    def test_get_nested_value_basic_access(self):
        """Test basic nested value access without interpolation."""
        config = {"dataset": {"num_classes": 10, "name": "cifar10"}, "model": {"layers": [1, 2, 3]}}

        engine = InterpolationEngine(config)

        assert engine._get_value_of_param("dataset.num_classes") == 10
        assert engine._get_value_of_param("dataset.name") == "cifar10"
        assert engine._get_value_of_param("model.layers") == [1, 2, 3]

    def test_get_nested_value_auto_interpolation_resolution(self):
        """Test that _get_nested_value automatically resolves interpolations."""
        config = {"base": {"value": 42}, "derived": {"ref": "${base.value}"}, "nested": {"chain": "${derived.ref}"}}

        engine = InterpolationEngine(config)

        # These should all return resolved values, not interpolation strings
        assert engine._get_value_of_param("base.value") == 42
        assert engine._get_value_of_param("derived.ref") == 42
        assert engine._get_value_of_param("nested.chain") == 42

    def test_get_nested_value_in_place_resolution(self):
        """Test that values are resolved in-place and stay resolved."""
        config = {"env_ref": "${TEST_ENV_VAR}", "param_ref": "${env_ref}"}

        # Set environment variable
        old_value = os.environ.get("TEST_ENV_VAR")
        os.environ["TEST_ENV_VAR"] = "test_value"

        try:
            engine = InterpolationEngine(config)

            # Resolve all interpolations in-place
            result = engine.resolve_all_interpolations()

            # Values should be resolved in the config itself
            assert config["env_ref"] == "test_value"
            assert config["param_ref"] == "test_value"
            assert result is config  # Same object

            # Change environment variable
            os.environ["TEST_ENV_VAR"] = "changed_value"

            # Accessing resolved values should return the in-place resolved values
            value2 = engine._get_value_of_param("env_ref")
            assert value2 == "test_value"  # Should be the in-place resolved value
            assert config["env_ref"] == "test_value"  # Config stays resolved

        finally:
            if old_value is None:
                os.environ.pop("TEST_ENV_VAR", None)
            else:
                os.environ["TEST_ENV_VAR"] = old_value

    def test_get_nested_value_circular_dependency_detection(self):
        """Test that _get_nested_value detects circular dependencies."""
        config = {"a": "${b}", "b": "${c}", "c": "${a}"}

        engine = InterpolationEngine(config)

        # Should raise CircularInterpolationError for any key in the cycle
        with pytest.raises(CircularInterpolationError) as exc_info:
            engine._get_value_of_param("a")

        # Check that cycle information is included
        error_msg = str(exc_info.value)
        assert "a" in error_msg and "b" in error_msg and "c" in error_msg

    def test_get_nested_value_mixed_resolution(self):
        """Test mixed scenarios with both resolvable and circular references."""
        config = {
            "normal": {"value": 100},
            "ref_normal": "${normal.value}",
            "circular_a": "${circular_b}",
            "circular_b": "${circular_a}",
            "ref_to_circular": "${circular_a}",
        }

        engine = InterpolationEngine(config)

        # Normal references should work
        assert engine._get_value_of_param("normal.value") == 100
        assert engine._get_value_of_param("ref_normal") == 100

        # Circular references should raise errors
        with pytest.raises(CircularInterpolationError):
            engine._get_value_of_param("circular_a")

        with pytest.raises(CircularInterpolationError):
            engine._get_value_of_param("ref_to_circular")

    def test_get_nested_value_recursive_interpolation_resolution(self):
        """Test recursive resolution of nested interpolations."""
        # Set up environment variables
        old_env = os.environ.get("BASE_SIZE")
        os.environ["BASE_SIZE"] = "64"

        try:
            config = {
                "level1": {"size": "${BASE_SIZE}"},
                "level2": {"ref": "${level1.size}"},
                "level3": {"final": "${level2.ref}"},
            }

            engine = InterpolationEngine(config)

            # Resolve all interpolations in-place
            engine.resolve_all_interpolations()

            # All values should be resolved in-place
            assert config["level1"]["size"] == 64
            assert config["level2"]["ref"] == 64
            assert config["level3"]["final"] == 64

            # Each level should resolve correctly when accessed
            assert engine._get_value_of_param("level1.size") == 64
            assert engine._get_value_of_param("level2.ref") == 64
            assert engine._get_value_of_param("level3.final") == 64

        finally:
            if old_env is None:
                os.environ.pop("BASE_SIZE", None)
            else:
                os.environ["BASE_SIZE"] = old_env

    def test_get_nested_value_type_conversion(self):
        """Test that numeric strings are properly converted to numbers."""
        # Set up environment variables with different types
        env_vars = {"INT_VAR": "42", "FLOAT_VAR": "3.14", "STRING_VAR": "hello"}

        old_values = {}
        for key, value in env_vars.items():
            old_values[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = {"int_ref": "${INT_VAR}", "float_ref": "${FLOAT_VAR}", "string_ref": "${STRING_VAR}"}

            engine = InterpolationEngine(config)

            # Check that types are converted correctly
            int_value = engine._get_value_of_param("int_ref")
            assert int_value == 42
            assert isinstance(int_value, int)

            float_value = engine._get_value_of_param("float_ref")
            assert float_value == 3.14
            assert isinstance(float_value, float)

            string_value = engine._get_value_of_param("string_ref")
            assert string_value == "hello"
            assert isinstance(string_value, str)

        finally:
            for key, old_value in old_values.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value

    def test_get_nested_value_key_not_found(self):
        """Test that missing keys raise appropriate KeyError."""
        config = {"existing": {"key": "value"}}

        engine = InterpolationEngine(config)

        with pytest.raises(KeyError, match="Key path 'nonexistent' not found"):
            engine._get_value_of_param("nonexistent")

        with pytest.raises(KeyError, match="Key path 'existing.nonexistent' not found"):
            engine._get_value_of_param("existing.nonexistent")

    def test_get_nested_value_engine_isolation(self):
        """Test that different engine instances work independently."""
        config1 = {"value": "${TEST_CACHE_VAR}"}
        config2 = {"value": "${TEST_CACHE_VAR}"}

        old_value = os.environ.get("TEST_CACHE_VAR")
        os.environ["TEST_CACHE_VAR"] = "initial"

        try:
            engine1 = InterpolationEngine(config1)
            engine2 = InterpolationEngine(config2)

            # Resolve in first engine
            engine1.resolve_all_interpolations()
            assert config1["value"] == "initial"

            # Change environment and resolve in second engine
            os.environ["TEST_CACHE_VAR"] = "changed"
            engine2.resolve_all_interpolations()
            assert config2["value"] == "changed"

            # First engine's config should still have resolved value
            assert config1["value"] == "initial"  # resolved in-place
            assert engine1._get_value_of_param("value") == "initial"

            # Second engine should have its own cached value
            value2_again = engine2._get_value_of_param("value")
            assert value2_again == "changed"  # cached

        finally:
            if old_value is None:
                os.environ.pop("TEST_CACHE_VAR", None)
            else:
                os.environ["TEST_CACHE_VAR"] = old_value

    def test_re_resolution_with_new_engine(self):
        """Test that new engine instances can resolve updated environment values."""
        config = {"ref": "${CLEAR_CACHE_TEST}"}

        old_value = os.environ.get("CLEAR_CACHE_TEST")
        os.environ["CLEAR_CACHE_TEST"] = "original"

        try:
            engine = InterpolationEngine(config)

            # Initial resolution
            engine.resolve_all_interpolations()
            assert config["ref"] == "original"

            # Change environment variable
            os.environ["CLEAR_CACHE_TEST"] = "modified"

            # Same engine should still return in-place resolved value
            value2 = engine._get_value_of_param("ref")
            assert value2 == "original"  # in-place resolved

            # New engine with fresh config should resolve to new value
            fresh_config = {"ref": "${CLEAR_CACHE_TEST}"}
            new_engine = InterpolationEngine(fresh_config)
            new_engine.resolve_all_interpolations()
            assert fresh_config["ref"] == "modified"  # newly resolved

        finally:
            if old_value is None:
                os.environ.pop("CLEAR_CACHE_TEST", None)
            else:
                os.environ["CLEAR_CACHE_TEST"] = old_value

    def test_complex_nested_interpolation_scenario(self):
        """Test complex scenarios with multiple levels and types of interpolation."""
        # Setup environment
        env_vars = {"MULTIPLIER": "3", "BASE_NUM": "5"}
        old_values = {}
        for key, value in env_vars.items():
            old_values[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = {
                "constants": {"pi": 3.14159},
                "env": {"multiplier": "${MULTIPLIER}", "base": "${BASE_NUM}"},
                "computed": {
                    "product": "${env.base}",  # Should be 5
                    "description": "value_${env.multiplier}",  # Should be "value_3"
                },
                "nested": {
                    "level1": "${computed.product}",  # Should be 5
                    "level2": "${nested.level1}",  # Should be 5
                    "level3": "${nested.level2}",  # Should be 5
                },
            }

            engine = InterpolationEngine(config)

            # Resolve all interpolations in-place first
            engine.resolve_all_interpolations()

            # Test all levels
            assert engine._get_value_of_param("constants.pi") == 3.14159
            assert engine._get_value_of_param("env.multiplier") == 3
            assert engine._get_value_of_param("env.base") == 5
            assert engine._get_value_of_param("computed.product") == 5
            assert engine._get_value_of_param("computed.description") == "value_3"
            assert engine._get_value_of_param("nested.level1") == 5
            assert engine._get_value_of_param("nested.level2") == 5
            assert engine._get_value_of_param("nested.level3") == 5

            # Verify all values are resolved in-place
            assert config["constants"]["pi"] == 3.14159
            assert config["env"]["multiplier"] == 3
            assert config["env"]["base"] == 5
            assert config["computed"]["product"] == 5
            assert config["computed"]["description"] == "value_3"
            assert config["nested"]["level1"] == 5
            assert config["nested"]["level2"] == 5
            assert config["nested"]["level3"] == 5

        finally:
            for key, old_value in old_values.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value
