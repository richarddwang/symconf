"""Test suite for parameter sweeping functionality."""

import sys
from pathlib import Path
from textwrap import dedent

from synconf import SynConfParser
from tests.conftest import write_yaml_file


def test_manual_sweeping(temp_dir: Path):
    """Test manual sweeping (手動遍歷).

    Given 準備包含插值邏輯的設置檔 and 在程式中定義遍歷邏輯
    When 執行遍歷
    Then 依序得到不同的設置組合
    """
    # Create config with interpolation logic
    config_data = {
        "dataset": "imagenet",
        "devices": [1, 2],
        "batch_size_per_device": "((`batch_size`//len(`devices`)))",  # Dynamic calculation
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    # Manual traversal logic
    parser = SynConfParser()
    results = []

    for dataset in ["iris", "cifar10"]:
        for batch_size in [32, 64]:
            if dataset == "iris" and batch_size == 32:
                continue  # Skip specific combination

            config = parser.parse_args([str(config_path), f"dataset={dataset}", f"batch_size={batch_size}"])

            results.append(
                {
                    "dataset": getattr(config, "dataset", None),
                    "batch_size": getattr(config, "batch_size", None),
                    "batch_size_per_device": getattr(config, "batch_size_per_device", None),
                }
            )

    # Verify expected combinations
    expected_combinations = [
        # iris + 32 is skipped
        {"dataset": "iris", "batch_size": 64, "batch_size_per_device": 32},  # 64//2
        {"dataset": "cifar10", "batch_size": 32, "batch_size_per_device": 16},  # 32//2
        {"dataset": "cifar10", "batch_size": 64, "batch_size_per_device": 32},  # 64//2
    ]

    assert len(results) == 3
    for expected in expected_combinations:
        assert expected in results


def test_simple_sweeping(temp_dir: Path):
    """Test simple parameter sweeping functionality.

    Uses the exact example from HOWTO.md 簡單遍歷 section:
    --sweep log.name=[my_((exp.seed)), REMOVE, hello] exp.seed=[0, 1, 2]
    """
    # Prepare config based on HOWTO.md example
    config_data = {
        "log": {"name": "default_log"},
        "exp": {"seed": 42},
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser()
    configs = parser.parse_args(
        [
            str(config_path),
            "--sweep",
            "log.name=[my_((exp.seed)), REMOVE, hello]",
            "exp.seed=[0, 1, 2]",
        ]
    )

    # Verify it returns a list of configs when using --sweep
    assert isinstance(configs, list)
    assert len(configs) == 9

    # Verify parameter order determines nesting (前面的參數為外層迴圈)
    # log.name should be outer loop, exp.seed should be inner loop
    expected_configs = []
    for log_name in ["my_((exp.seed))", "REMOVE", "hello"]:  # 前面的參數為外層迴圈
        for exp_seed in [0, 1, 2]:  # 後面的參數為內層迴圈
            config = parser.parse_args([str(config_path), f"log.name={log_name}", f"exp.seed={exp_seed}"])
            expected_configs.append(config)

    # Compare the actual data rather than object equality
    assert len(configs) == len(expected_configs)
    for i, (actual, expected) in enumerate(zip(configs, expected_configs)):
        assert actual.exp.seed == expected.exp.seed, f"Config {i}: exp.seed mismatch"
        # Handle REMOVE case where log section might be removed
        if hasattr(expected, "log"):
            assert hasattr(actual, "log"), f"Config {i}: actual missing log section"
            assert actual.log.name == expected.log.name, f"Config {i}: log.name mismatch"
        else:
            assert not hasattr(actual, "log"), f"Config {i}: actual should not have log section"


def test_complex_sweeping(temp_dir: Path):
    """Test complex parameter sweeping.

    Given 定義自定義的參數組合生成函式
    When 使用自定義函式進行遍歷
    Then 系統按照自定義邏輯產生參數組合
    """
    config_data = {
        "model": {"batch_size": 1},
        "exp": {"seed": 0},
        "log": {"name": "default"},
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    # Create a custom sweep function file
    sweep_function_content = '''
    from typing import Iterator

    def custom_sweep() -> Iterator[list[str]]:
        """Custom parameter combination generator."""
        for model_batch_size in [2, 4, 6]:
            for exp_seed, name in [(0, "first"), (1, "second"), (2, "third")]:
                if model_batch_size == 2 and exp_seed == 0:
                    continue  # Skip specific combination
                yield [
                    f"model.batch_size={model_batch_size}",
                    f"exp.seed={exp_seed}",
                    f"log.name={name}",
                ]
    '''

    sweep_file = temp_dir / "my_sweep.py"
    with open(sweep_file, "w") as f:
        f.write(dedent(sweep_function_content))

    # Add temp directory to path so we can import the sweep function
    sys.path.insert(0, str(temp_dir))

    try:
        parser = SynConfParser()
        configs = parser.parse_args([str(config_path), "--sweep", "my_sweep.custom_sweep"])

        assert isinstance(configs, list)

        # Verify expected combinations (excluding skipped one)
        # Total: 3 batch_sizes × 3 seeds - 1 skipped = 8 combinations
        assert len(configs) == 8

        # Verify skipped combination is not present
        skipped_found = False
        for config in configs:
            if (
                hasattr(config, "model")
                and hasattr(config, "exp")
                and getattr(config.model, "batch_size", None) == 2
                and getattr(config.exp, "seed", None) == 0
            ):
                skipped_found = True
                break

        assert not skipped_found, "Skipped combination should not be present"

    finally:
        # Clean up sys.path
        sys.path.remove(str(temp_dir))
