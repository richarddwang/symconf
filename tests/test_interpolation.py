"""Tests for interpolation functionality."""

import os

import pytest
import yaml

from twinconf import TwinConfParser


class TestVariableInterpolation:
    """Test variable interpolation functionality."""

    def test_simple_variable_interpolation(self, temp_dir):
        """Test simple ${var} interpolation."""
        config_data = {
            "dataset": {"num_classes": 10},
            "output_features": "${dataset.num_classes}",
            "name": "n=${dataset.num_classes}",
            "dummy": "1${dataset.num_classes}",
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        assert config.output_features == 10
        assert config.name == "n=10"
        assert config.dummy == "110"
        assert config.dataset.num_classes == 10

    def test_environment_variable_interpolation(self, temp_dir):
        """Test interpolation with environment variables."""
        # Set environment variable
        os.environ["NUM_CLASSES"] = "20"

        try:
            config_data = {"dataset": {"num_classes": "${NUM_CLASSES}"}, "output_features": "${dataset.num_classes}"}
            config_file = temp_dir / "config.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config_data, f)

            parser = TwinConfParser()
            config = parser.parse_args([str(config_file)])

            assert config.dataset.num_classes == 20
            assert config.output_features == 20

        finally:
            # Clean up environment variable
            del os.environ["NUM_CLASSES"]

    def test_missing_variable_interpolation(self, temp_dir):
        """Test error handling for missing variables."""
        config_data = {"value": "${missing_var}"}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()

        with pytest.raises(KeyError, match="Variable 'missing_var' not found"):
            parser.parse_args([str(config_file)])


class TestExpressionInterpolation:
    """Test expression interpolation functionality."""

    def test_simple_expression_interpolation(self, temp_dir):
        """Test ${`var` + `var`} expression interpolation."""
        config_data = {
            "dataset": {"num_classes": 10},
            "model": {"extra_outputs": 2, "output_features": "${`dataset.num_classes` + `model.extra_outputs`}"},
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        assert config.model.output_features == 12
        assert config.dataset.num_classes == 10
        assert config.model.extra_outputs == 2

    def test_complex_expression_interpolation(self, temp_dir):
        """Test more complex expressions."""
        config_data = {
            "values": {"a": 5, "b": 3},
            "result1": "${`values.a` * `values.b`}",
            "result2": "${`values.a` // `values.b`}",
            "result3": "${`values.a` ** 2}",
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        assert config.result1 == 15  # 5 * 3
        assert config.result2 == 1  # 5 // 3
        assert config.result3 == 25  # 5 ** 2

    def test_expression_with_environment_variables(self, temp_dir):
        """Test expressions with environment variables."""
        os.environ["BASE_VALUE"] = "100"

        try:
            config_data = {"multiplier": 2, "result": "${`BASE_VALUE` * `multiplier`}"}
            config_file = temp_dir / "config.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config_data, f)

            parser = TwinConfParser()
            config = parser.parse_args([str(config_file)])

            assert config.result == 200  # 100 * 2

        finally:
            del os.environ["BASE_VALUE"]

    def test_expression_error_handling(self, temp_dir):
        """Test error handling for invalid expressions."""
        config_data = {
            "dataset": {"num_classes": 10},
            "result": "${`dataset.num_classes` / 0}",  # Division by zero
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()

        with pytest.raises(ValueError, match="Error evaluating expression"):
            parser.parse_args([str(config_file)])
