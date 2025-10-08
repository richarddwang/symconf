"""Simple test to verify SymConfConfig behavior and fix test assumptions."""

import os
import sys
import tempfile

import yaml

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_actual_behavior():
    """Test actual SymConfConfig behavior to inform proper test writing."""
    from symconf import SymConfParser

    # Create test config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_data = {
            "model": {
                "learning_rate": 1e-4,
                "batch_size": 32,
            },
            "training": {"epochs": 100},
        }
        yaml.dump(config_data, f)
        config_path = f.name

    try:
        parser = SymConfParser()
        config = parser.parse_args([config_path])

        print("=== Basic Access Tests ===")
        print(f"Type of config: {type(config)}")
        print(f"config attributes available: {list(config.__dict__.keys())}")

        # Test attribute access
        print(f"config.model exists: {hasattr(config, 'model')}")
        if hasattr(config, "model"):
            print(f"config.model: {config.model}")
            print(f"config.model.learning_rate: {config.model.learning_rate}")

        # Test dict access
        print(f"Dict access config['model']: {config['model']}")
        print(f"Dict access config['model']['learning_rate']: {config['model']['learning_rate']}")

        print("\n=== Sweep Test ===")
        # Test sweeping
        configs = parser.parse_args([config_path, "--sweep.model.learning_rate", "1e-3", "1e-5"])
        print(f"Type of sweep result: {type(configs)}")
        print(f"Length of sweep result: {len(configs)}")

        if isinstance(configs, list):
            for i, cfg in enumerate(configs):
                print(f"Config {i}: model.learning_rate = {cfg.model.learning_rate}")

    finally:
        os.unlink(config_path)


if __name__ == "__main__":
    test_actual_behavior()
