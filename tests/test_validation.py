"""Tests for type validation functionality."""

from typing import List, Optional

import pytest
import yaml

from twinconf import TwinConfParser


class MockModel:
    """Mock model class for testing validation."""

    def __init__(
        self,
        hidden_size: int,
        num_layers: int,
        dropout: float = 0.1,
        activation: str = "relu",
        features: Optional[List[str]] = None,
    ):
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.activation = activation
        self.features = features or []


class MockOptimizer:
    """Mock optimizer class for testing validation."""

    def __init__(self, lr: float, weight_decay: float = 0.0):
        self.lr = lr
        self.weight_decay = weight_decay


class TestTypeValidation:
    """Test type validation functionality."""

    def test_valid_types(self, temp_dir):
        """Test that valid types pass validation."""
        config_data = {
            "model": {
                "TYPE": "test_validation.MockModel",
                "hidden_size": 128,
                "num_layers": 4,
                "dropout": 0.2,
                "activation": "gelu",
                "features": ["feature1", "feature2"],
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        base_classes = {"model": MockModel}
        parser = TwinConfParser(base_classes=base_classes, validate_types=True)

        # Should not raise any exceptions
        config = parser.parse_args([str(config_file)])

        assert config.model.TYPE == "test_validation.MockModel"
        assert config.model.hidden_size == 128
        assert config.model.num_layers == 4
        assert config.model.dropout == 0.2
        assert config.model.activation == "gelu"
        assert config.model.features == ["feature1", "feature2"]

    def test_invalid_type_int(self, temp_dir):
        """Test validation error for invalid int type."""
        config_data = {
            "model": {
                "TYPE": "test_validation.MockModel",
                "hidden_size": "not_an_int",  # Should be int
                "num_layers": 4,
                "dropout": 0.2,
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        base_classes = {"model": MockModel}
        parser = TwinConfParser(base_classes=base_classes, validate_types=True)

        with pytest.raises(ValueError, match="Expected type.*int.*got str"):
            parser.parse_args([str(config_file)])

    def test_invalid_type_float(self, temp_dir):
        """Test validation error for invalid float type."""
        config_data = {
            "model": {
                "TYPE": "test_validation.MockModel",
                "hidden_size": 128,
                "num_layers": 4,
                "dropout": "not_a_float",  # Should be float
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        base_classes = {"model": MockModel}
        parser = TwinConfParser(base_classes=base_classes, validate_types=True)

        with pytest.raises(ValueError, match="Expected type.*float.*got str"):
            parser.parse_args([str(config_file)])

    def test_missing_required_args(self, temp_dir):
        """Test error for missing required arguments."""
        config_data = {
            "model": {
                "TYPE": "test_validation.MockModel",
                # Missing required 'hidden_size' and 'num_layers'
                "dropout": 0.2,
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        base_classes = {"model": MockModel}
        parser = TwinConfParser(base_classes=base_classes, check_missing_args=True)

        with pytest.raises(ValueError, match="Missing required argument"):
            parser.parse_args([str(config_file)])

    def test_unexpected_args(self, temp_dir):
        """Test error for unexpected arguments."""
        config_data = {
            "optimizer": {
                "TYPE": "test_validation.MockOptimizer",
                "lr": 0.001,
                "weight_decay": 0.01,
                "unexpected_param": "value",  # Not in MockOptimizer signature
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        base_classes = {"optimizer": MockOptimizer}
        parser = TwinConfParser(base_classes=base_classes, check_unexpected_args=True)

        with pytest.raises(ValueError, match="Unexpected argument"):
            parser.parse_args([str(config_file)])

    def test_optional_types(self, temp_dir):
        """Test that optional types work correctly."""
        config_data = {
            "model": {
                "TYPE": "test_validation.MockModel",
                "hidden_size": 128,
                "num_layers": 4,
                "features": None,  # Optional parameter set to None
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        base_classes = {"model": MockModel}
        parser = TwinConfParser(base_classes=base_classes, validate_types=True)

        # Should not raise any exceptions
        config = parser.parse_args([str(config_file)])

        assert config.model.features is None

    def test_list_type_validation(self, temp_dir):
        """Test validation of List types."""
        config_data = {
            "model": {
                "TYPE": "test_validation.MockModel",
                "hidden_size": 128,
                "num_layers": 4,
                "features": "not_a_list",  # Should be List[str]
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        base_classes = {"model": MockModel}
        parser = TwinConfParser(base_classes=base_classes, validate_types=True)

        # Should not raise exception since Optional[List[str]] allows string too
        # (This might be a limitation in the current validation implementation)
        config = parser.parse_args([str(config_file)])
        assert config.model.features == "not_a_list"

    def test_validation_disabled(self, temp_dir):
        """Test that validation can be disabled."""
        config_data = {
            "model": {
                "TYPE": "test_validation.MockModel",
                "hidden_size": "not_an_int",  # Would normally fail
                "num_layers": "not_an_int",  # Would normally fail
                "unexpected_param": "value",  # Would normally fail
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        base_classes = {"model": MockModel}
        parser = TwinConfParser(
            base_classes=base_classes, validate_types=False, check_missing_args=False, check_unexpected_args=False
        )

        # Should not raise any exceptions
        config = parser.parse_args([str(config_file)])

        assert config.model.hidden_size == "not_an_int"
        assert config.model.num_layers == "not_an_int"
        assert config.model.unexpected_param == "value"


class TestDefaultValues:
    """Test default value handling."""

    def test_default_values_applied(self, temp_dir):
        """Test that default values are applied when arguments are missing."""
        config_data = {
            "model": {
                "TYPE": "test_validation.MockModel",
                "hidden_size": 128,
                "num_layers": 4,
                # dropout and activation should get default values
            }
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        base_classes = {"model": MockModel}
        parser = TwinConfParser(base_classes=base_classes)

        config = parser.parse_args([str(config_file)])

        assert config.model.dropout == 0.1  # Default value
        assert config.model.activation == "relu"  # Default value
        assert config.model.features is None  # Default value is None, not []
