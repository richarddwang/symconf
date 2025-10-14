"""Test cases for SynConf list manipulation (操控 list).

This module tests list manipulation functionality following HOWTO.md structure.
"""

from pathlib import Path

from synconf import SynConfParser
from tests.conftest import write_yaml_file


def test_basic_list_type_functionality(temp_dir: Path):
    """Test basic LIST type functionality.

    Given 準備基礎的 list 設置 and 準備覆寫設置來修改 list 內容
    When 傳入多個檔案解析設置
    Then 得到修改後的 list
    """
    # Create base list configuration
    base_config = {
        "callbacks": {
            "TYPE": "LIST",
            "log": "log_callback",
            "ckpt": "save_model_callback",
            "debug": "debug_callback",
        }
    }
    base_path = temp_dir / "base.yaml"
    write_yaml_file(base_path, base_config)

    # Create override configuration
    override_config = {
        "callbacks": {
            "TYPE": "LIST",
            "ckpt": "REMOVE",  # Remove specific item
            "stop": "early_stopping_callback",  # Add new item
        }
    }
    override_path = temp_dir / "override.yaml"
    write_yaml_file(override_path, override_config)

    # Parse with list manipulation
    parser = SynConfParser()
    config = parser.parse_args([str(base_path), str(override_path)])

    # Verify list manipulation results
    callbacks = config.callbacks

    # Should be a list, not dict
    assert isinstance(callbacks, list)

    # Should contain expected items
    assert "log_callback" in callbacks  # Preserved
    assert "debug_callback" in callbacks  # Preserved
    assert "early_stopping_callback" in callbacks  # Added
    assert "save_model_callback" not in callbacks  # Removed
