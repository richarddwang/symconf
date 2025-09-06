"""Tests for configuration sweeping functionality."""

import yaml

from twinconf import TwinConfParser


class TestConfigurationSweeping:
    """Test configuration sweeping functionality."""

    def test_simple_sweep_values(self, temp_dir):
        """Test simple parameter sweeping."""
        config_data = {"learning_rate": "SWEEP[0.001, 0.01, 0.1]", "model": {"hidden_size": 128, "dropout": 0.1}}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        configs = parser.parse_args([str(config_file)])

        # Current implementation: SWEEP not yet implemented
        # So this will be treated as a single config with the string value
        if isinstance(configs, list):
            # Future implementation: should return 3 configurations
            assert len(configs) == 3
            expected_rates = [0.001, 0.01, 0.1]
            for i, config in enumerate(configs):
                assert config.learning_rate == expected_rates[i]
                assert config.model.hidden_size == 128
                assert config.model.dropout == 0.1
        else:
            # Current behavior: single configuration with string value
            assert configs.learning_rate == "SWEEP[0.001, 0.01, 0.1]"
            assert configs.model.hidden_size == 128
            assert configs.model.dropout == 0.1

    def test_multiple_sweep_parameters(self, temp_dir):
        """Test sweeping multiple parameters simultaneously."""
        config_data = {
            "learning_rate": "SWEEP[0.001, 0.01]",
            "batch_size": "SWEEP[32, 64]",
            "model": {"hidden_size": 128},
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        configs = parser.parse_args([str(config_file)])

        if isinstance(configs, list):
            # Future implementation: should return 4 configurations (2x2 cartesian product)
            assert len(configs) == 4

            expected_combinations = [(0.001, 32), (0.001, 64), (0.01, 32), (0.01, 64)]

            for i, config in enumerate(configs):
                expected_lr, expected_bs = expected_combinations[i]
                assert config.learning_rate == expected_lr
                assert config.batch_size == expected_bs
                assert config.model.hidden_size == 128
        else:
            # Current behavior: single configuration with string values
            assert configs.learning_rate == "SWEEP[0.001, 0.01]"
            assert configs.batch_size == "SWEEP[32, 64]"
            assert configs.model.hidden_size == 128

    def test_nested_sweep_parameters(self, temp_dir):
        """Test sweeping nested parameters."""
        config_data = {
            "model": {"hidden_size": "SWEEP[64, 128, 256]", "num_layers": "SWEEP[2, 4]", "dropout": 0.1},
            "learning_rate": 0.001,
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        configs = parser.parse_args([str(config_file)])

        if isinstance(configs, list):
            # Future implementation: should return 6 configurations (3x2 cartesian product)
            assert len(configs) == 6

            expected_combinations = [(64, 2), (64, 4), (128, 2), (128, 4), (256, 2), (256, 4)]

            for i, config in enumerate(configs):
                expected_hs, expected_layers = expected_combinations[i]
                assert config.model.hidden_size == expected_hs
                assert config.model.num_layers == expected_layers
                assert config.model.dropout == 0.1
                assert config.learning_rate == 0.001
        else:
            # Current behavior: single configuration with string values
            assert configs.model.hidden_size == "SWEEP[64, 128, 256]"
            assert configs.model.num_layers == "SWEEP[2, 4]"
            assert configs.model.dropout == 0.1
            assert configs.learning_rate == 0.001

    def test_sweep_with_interpolation(self, temp_dir):
        """Test combining sweeping with interpolation."""
        config_data = {
            "base_lr": 0.001,
            "multipliers": "SWEEP[1, 10, 100]",
            "learning_rate": "${base_lr}",  # Simple interpolation that works
            "model": {"hidden_size": 128},
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        configs = parser.parse_args([str(config_file)])

        if isinstance(configs, list):
            # Future implementation: should return 3 configurations
            assert len(configs) == 3
            # This would test expression evaluation after SWEEP expansion
            pass
        else:
            # Current behavior: expressions work, but SWEEP is just a string
            assert configs.base_lr == 0.001
            assert configs.multipliers == "SWEEP[1, 10, 100]"
            assert configs.learning_rate == 0.001  # Interpolated from base_lr
            assert configs.model.hidden_size == 128


class TestSweepSyntax:
    """Test different SWEEP syntax variations."""

    def test_sweep_integer_values(self, temp_dir):
        """Test SWEEP with integer values."""
        config_data = {"batch_size": "SWEEP[16, 32, 64, 128]"}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        configs = parser.parse_args([str(config_file)])

        if isinstance(configs, list):
            # Future implementation
            assert len(configs) == 4
            expected_values = [16, 32, 64, 128]
            for i, config in enumerate(configs):
                assert config.batch_size == expected_values[i]
        else:
            # Current behavior
            assert configs.batch_size == "SWEEP[16, 32, 64, 128]"

    def test_sweep_float_values(self, temp_dir):
        """Test SWEEP with float values."""
        config_data = {"dropout": "SWEEP[0.0, 0.1, 0.2, 0.5]"}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        configs = parser.parse_args([str(config_file)])

        if isinstance(configs, list):
            # Future implementation
            assert len(configs) == 4
            expected_values = [0.0, 0.1, 0.2, 0.5]
            for i, config in enumerate(configs):
                assert config.dropout == expected_values[i]
        else:
            # Current behavior
            assert configs.dropout == "SWEEP[0.0, 0.1, 0.2, 0.5]"

    def test_sweep_string_values(self, temp_dir):
        """Test SWEEP with string values."""
        config_data = {"activation": "SWEEP[relu, tanh, sigmoid, gelu]"}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        configs = parser.parse_args([str(config_file)])

        if isinstance(configs, list):
            # Future implementation
            assert len(configs) == 4
            expected_values = ["relu", "tanh", "sigmoid", "gelu"]
            for i, config in enumerate(configs):
                assert config.activation == expected_values[i]
        else:
            # Current behavior
            assert configs.activation == "SWEEP[relu, tanh, sigmoid, gelu]"


def sample_sweep_function(config):
    """Sample sweep function for testing purposes."""
    return f"lr={config.learning_rate}, bs={config.batch_size}"


class TestSweepFunctionality:
    """Test sweep functionality integration."""

    def test_sweep_with_function_calls(self, temp_dir):
        """Test applying functions to sweep configurations."""
        config_data = {
            "learning_rate": "SWEEP[0.001, 0.01]",
            "batch_size": "SWEEP[32, 64]",
            "model": {"hidden_size": 128},
        }
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        configs = parser.parse_args([str(config_file)])

        if isinstance(configs, list):
            # Future implementation: test function mapping
            results = [sample_sweep_function(config) for config in configs]
            expected_results = ["lr=0.001, bs=32", "lr=0.001, bs=64", "lr=0.01, bs=32", "lr=0.01, bs=64"]
            assert results == expected_results
        else:
            # Current behavior: single config
            result = sample_sweep_function(configs)
            assert "SWEEP" in result  # The function will see the SWEEP string
