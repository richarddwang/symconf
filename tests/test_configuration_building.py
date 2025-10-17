"""Test cases for SynConf configuration building (構建設置).

This module tests the core configuration building functionality following HOWTO.md structure.
"""

from pathlib import Path
from textwrap import dedent

import pytest

import tests
from synconf import CircularInterpolationError, ParameterValidationError, SynConfParser
from tests.conftest import cleanup_env_vars, set_env_vars, write_yaml_file


def test_step1_load_yaml_and_overrides(temp_dir: Path):
    """Test Step 1: Sequential loading of configurations and parameter overrides.

    Given 準備多個 YAML 檔案和參數覆寫
    When 交替使用檔案和參數覆寫
    Then 按順序依序應用每個設置，得到最終結果
    """
    # Following HOWTO.md Step 1 example exactly
    # Create base.yaml
    base_data = {
        "server": {
            "port": 8080,
            "timeout": 30,
        },
        "exp": {
            "seed": 42,
        },
    }
    base_path = temp_dir / "base.yaml"
    write_yaml_file(base_path, base_data)

    # Create override.yaml
    override_data = {
        "server": {
            "timeout": 10,
            "debug": True,
        }
    }
    override_path = temp_dir / "override.yaml"
    write_yaml_file(override_path, override_data)

    # Test NEW syntax: base.yaml exp.timeout=100 server.host=localhost override.yaml server.port=9090
    parser = SynConfParser()
    config = parser.parse_args(
        [str(base_path), "exp.timeout=100", "server.host=localhost", str(override_path), "server.port=9090"]
    )

    # Verify the exact expected results from HOWTO.md
    assert config.server.host == "localhost"  # 來自命令列參數覆寫
    assert config.server.port == 9090  # 來自 base.yaml -> 命令列參數覆寫
    assert config.server.timeout == 10  # 來自 base.yaml -> 命令列參數覆寫 -> override.yaml
    assert config.server.debug is True  # 來自 override.yaml
    assert config.exp.timeout == 100  # 來自 base.yaml (changed by override)


def test_step2_remove_parameters(temp_dir: Path):
    """Test Step 2: Removing parameters using REMOVE keyword.

    Given 準備基礎設置檔案 and 準備覆寫設置檔案來移除特定參數
    When 傳入多個檔案解析設置
    Then 得到移除指定參數後的設置
    """
    # Create default config
    default_config = {
        "server": {
            "host": "localhost",
            "timeout": 10,
            "port": 9090,
            "debug": True,
        }
    }
    default_path = temp_dir / "default.yaml"
    write_yaml_file(default_path, default_config)

    # Create override config with REMOVE
    override_config = {"server": {"debug": "REMOVE"}}
    override_path = temp_dir / "override.yaml"
    write_yaml_file(override_path, override_config)

    # Parse with removal using new syntax
    parser = SynConfParser()
    config = parser.parse_args([str(default_path), str(override_path), "server.port=REMOVE"])

    # Verify removal
    assert config.server.host == "localhost"
    assert config.server.timeout == 10
    assert not hasattr(config.server, "debug")  # Should be removed
    assert not hasattr(config.server, "port")  # Should be removed


def test_step3_complex_kwargs_chain_completion(temp_dir: Path):
    """Test Step 3: Complex **kwargs chain parameter default completion.

    Given 定義帶有預設參數的物件 with **kwargs chain (func -> BaseModel -> AwesomeModel)
    And 準備只設定部分參數的設置
    When 解析設置
    Then 系統自動補全預設值，得到設置等同於 HOWTO.md example
    """
    # Following the exact HOWTO.md Step 4 example
    config_data = {
        "model": {
            "TYPE": "tests.data.completion.AwesomeModel",
            "act": "relu",  # Parameter for func() via **kwargs chain
            "learning_rate": 1e-4,  # Parameter for BaseModel, user explicitly set
            # message should be auto-completed from func() default
            # loss_scale should be auto-completed from AwesomeModel default
            # batch_size is NOT included as it's overridden in AwesomeModel.__init__
        }
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser(validate_type=False, validate_mapping=False)
    config = parser.parse_args([str(config_path)])

    # Verify completion following HOWTO.md expectations
    assert config.model.TYPE == "tests.data.completion.AwesomeModel"
    assert config.model.act == "relu"  # 使用者設定的值
    assert config.model.learning_rate == 1e-4  # 使用者明確設定的參數不會被覆寫
    assert config.model.message == "hello"  # 自動補全的預設值 from func()
    assert config.model.loss_scale == 1.0  # 自動補全的預設值 from AwesomeModel
    assert not hasattr(config.model, "batch_size")  # batch_size 非 AwesomeModel 可設定的參數 (overridden)


def test_step4_variable_interpolation_comprehensive(temp_dir: Path):
    """Test Step 4: Variable interpolation (引用變數值) - comprehensive test.

    Given 展示三種插值和遞迴引用的綜合範例 and 設定環境變數
    When 解析設置
    Then 所有插值被遞迴解析為實際值

    Tests all three interpolation types with both old ${...} and new ((...)) syntax:
    - 參數插值 ((simple_name)): referencing config parameters
    - 環境變數插值 ((UPPER_CASE)): referencing environment variables
    - 表達式插值 ((... `variable` ...)): executing Python expressions with backtick variables
    """
    # Set environment variables as in HOWTO.md example
    set_env_vars(FEATURE_SIZE="64")

    try:
        # Following the exact HOWTO.md Step 4 comprehensive example
        config_data = {
            "dataset": {"num_classes": 10},
            "model": {
                # 參數插值（直接引用）
                "output_features": "((dataset.num_classes))",
                # 環境變數插值
                "hidden_dim": "((FEATURE_SIZE))",
                # 表達式插值
                "dropout": '((int("`FEATURE_SIZE`"[1]) / `model.output_features`))',
            },
            # 嵌入字串中使用 / 遞回引用
            "name": "model_f=((model.output_features))_h=((model.hidden_dim))",
        }
        config_path = temp_dir / "config.yaml"
        write_yaml_file(config_path, config_data)

        parser = SynConfParser()
        config = parser.parse_args([str(config_path)])

        # Verify all interpolation types work as expected from HOWTO.md
        assert config.dataset.num_classes == 10  # 原始值

        assert config.model.output_features == 10  # 參數插值: dataset.num_classes
        assert (
            config.model.hidden_dim == 64
        )  # 環境變數插值: FEATURE_SIZE。環境變數在是 str 類型，但插值結果會被 YAML 讀取，因此會自動轉換為適當的型別
        assert config.model.dropout == 0.4  # 表達式插值: 4 / 10 = 0.4

        assert config.name == "model_f=10_h=64"  # 字串嵌入/遞迴引用

    finally:
        cleanup_env_vars("FEATURE_SIZE")


def test_step4_circular_dependency_detection(temp_dir: Path):
    """Test circular dependency detection in interpolation.

    Given 插值形成循環引用
    When 解析時有循環依賴
    Then 顯示循環插值錯誤
    """
    config_data = {
        "a": "((b))",
        "b": "((c))",
        "c": 3,
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser()

    # Create circular dependency via command line
    with pytest.raises(CircularInterpolationError) as exc_info:
        parser.parse_args(
            [
                str(config_path),
                "c=((a))",  # Creates circular dependency: a -> b -> c -> a
            ]
        )

        # Verify error message contains the circular chain
        error_msg = str(exc_info.value)
        message = """
            a: ${b}
            → b: ${c}
            → c: ${a}
            → a: ${b}
            """
        assert dedent(message).rstrip() in error_msg


def test_step5_type_validation(temp_dir: Path):
    """Test Step 5: Type validation.

    Given 定義範例類別和函式 and 初始化 `SynConfParser` 並指定 base_classes and 準備包含各種型別情況的設置
    When 解析設置
    Then 系統一次性報告所有參數驗證錯誤
    """
    yaml_content = """
        model:
            TYPE: tests.data.validation.Child
            percent: 1                           # 錯誤：應該要是 float
            animal: pig                          # 錯誤：值應該是 'cat' 或 'dog' 
            precision: bf16                      # 正確：符合 Literal 限制 
            dummy: false                         # 正確：無型別註解不檢查
            toy:                                 # 正確：物件返回值符合型別
                TYPE: tests.data.validation.SuperToy 
            stoy:                                # 錯誤：Toy 不是 SuperToy
                TYPE: tests.data.validation.Toy         
            toy_cls: !!python/name:tests.data.validation.Toy  # 正確：使用 PyYAML 標籤傳入類別本身
            stoy_cls:                            # 錯誤：期待型別而非實例
                TYPE: tests.data.validation.SuperToy
            number:                              # 正確：函式返回值符合型別
                TYPE: tests.data.realization.square
                value: 0.3
            name: null                           # 正確：以子類別定義為準
            vocab: [a, b]                        # 正確：容器型別只檢查第一層
            
        """
    config_path = temp_dir / "config.yaml"
    with open(config_path, "w") as f:
        f.write(dedent(yaml_content).strip())

    parser = SynConfParser(
        validate_type=True,
        base_classes={"model": tests.data.validation.Parent},
        validate_exclude=["model.dummy2"],  # 不驗證這些參數，as shown in HOWTO.md
    )

    with pytest.raises(ParameterValidationError) as exc_info:
        parser.parse_args([str(config_path)])

    error_msg = str(exc_info.value)
    print("Actual error message:")
    print(repr(error_msg))

    # Just check that we have type validation errors as expected
    message = """
        ❌ Type mismatch
        Parameter: model.percent
        Expected: float
        Actual: 1 (int)

        ❌ Type mismatch
        Parameter: model.animal
        Expected: Literal['cat', 'dog']
        Actual: 'pig' (str)

        ❌ Type mismatch
        Parameter: model.stoy
        Expected: Optional[tests.data.validation.SuperToy]
        Actual: ... (tests.data.validation.Toy)

        ❌ Type mismatch
        Parameter: model.stoy_cls
        Expected: Type[tests.data.validation.SuperToy]
        Actual: ... (tests.data.validation.SuperToy)
        """
    assert set(dedent(message).strip().split("\n\n")) == set(error_msg.split("\n\n"))


def test_step5_parameter_mapping_validation(temp_dir: Path):
    """Test Step 5: Parameter mapping validation.

    Given 物件定義 and 初始化有啟用參數對應性檢查的 `SynConfParser` and 準備包含參數錯誤的設置
    When 解析設置
    Then 系統一次性報告所有參數驗證錯誤
    """
    config_data = {
        "model": {
            "TYPE": "tests.data.mapping.Child",
            # Missing required parameter 'a'
            # Missing required parameter 'd' (for parent)
            "c": 5,  # Unexpected parameter
            "e": 7,  # Unexpected parameter
        },
        "fn": {
            "TYPE": "tests.data.mapping.func",
            "x": 3.0,  # Correct parameter
            "z": 5,  # Unexpected parameter
        },
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser(
        validate_mapping=True,
        validate_exclude=["model.a"],  # 排除不檢查的參數，as shown in HOWTO.md
    )

    with pytest.raises(ParameterValidationError) as exc_info:
        parser.parse_args([str(config_path)])

    error_msg = str(exc_info.value)
    print("Actual error message:")
    print(repr(error_msg))

    # The test expects Child to have different parameters than what's in mapping.py
    message = """
        ❌ Missing parameters
        Parameters: model.d
        Object: tests.data.mapping.Child

        ❌ Unexpected parameters
        Parameters: model.c, model.e
        Object: tests.data.mapping.Child

        ❌ Unexpected parameters
        Parameters: fn.z
        Object: tests.data.mapping.func

        ❌ Type mismatch
        Parameter: fn.x
        Expected: int
        Actual: 3.0 (float)
        """
    assert set(dedent(message).strip().split("\n\n")) == set(error_msg.split("\n\n"))
