"""Test cases for SynConf help functionality (獲取幫助).

This module tests the help and configuration viewing functionality following HOWTO.md structure.
"""

from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest

from synconf import SynConfParser
from tests.conftest import write_yaml_file


def test_print_complete_configuration(temp_dir: Path, capsys):
    """Test viewing complete configuration (檢視完整設置).

    When 使用 `--print` 參數執行程式
    Then 系統會以 YAML 形式，印出經過所有步驟處理後的最終完整設置內容，並提示按 Enter 鍵確認後才繼續執行程式
    """
    # Create a complex configuration
    config_data = {
        "server": {"host": "localhost", "port": 8080},
        "model": {
            "TYPE": "tests.data.realization.AwesomeModel",
            "learning_rate": 1e-3,
        },
        "training": {"epochs": 100},
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    # Mock input to simulate user pressing Enter
    with patch("builtins.input", return_value=""):
        parser = SynConfParser(validate_type=False, validate_mapping=False)
        parser.parse_args([str(config_path), "--print"])

    # Verify print output contains the configuration
    captured = capsys.readouterr()
    assert "Final Configuration:" in captured.out
    assert "server:" in captured.out
    assert "model:" in captured.out
    assert "training:" in captured.out


def test_object_parameter_help_with_kwargs_chain(temp_dir: Path, capsys):
    """Test object parameter help with **kwargs parameter chain.

    Tests **kwargs tracing through inheritance chain as shown in HOWTO.md.

    NOTE: This test uses the existing Child->Parent chain in conftest.py to verify
    that kwargs parameter tracing works through super() calls. The full HOWTO.md example
    (Child -> Parent -> AClass.create -> func -> BClass.my_method) would require
    improved kwargs resolution for class method calls.
    """
    parser = SynConfParser()

    with pytest.raises(SystemExit):  # --help.object causes sys.exit(0)
        parser.parse_args(["--help.object=tests.data.kwargs_chain.Child"])

    captured = capsys.readouterr()
    output = captured.out

    message = """
        tests.data.kwargs_chain.Child:
            d
        → tests.data.kwargs_chain.Parent:
            b(Literal['cat', 'dog'])
        → tests.data.kwargs_chain.AClass.create:
            e(default='hi')
        → tests.data.kwargs_chain.func:
            f(int, default=5): 狐狸
        → tests.data.kwargs_chain.BClass.my_method:
            g(float): 猩猩
        """
    assert dedent(message).strip() in output
