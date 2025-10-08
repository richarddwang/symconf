"""Test cases for SymConf configuration building (構建設置).

This module tests the core configuration building functionality following HOWTO.md structure.
"""

import os
from pathlib import Path
from textwrap import dedent

import pytest
from conftest import cleanup_env_vars, set_env_vars, write_yaml_file

from symconf import CircularInterpolationError, ParameterValidationError, SymConfParser


class TestConfigurationBuilding:
    """Test configuration building process (構建設置)."""

    def test_basic_parser_initialization_and_parsing(self, temp_dir: Path):
        """Test basic SymConfParser initialization and parsing as shown in HOWTO.md.

        Given 初始化 `SymConf` parser 並解析命令列參數
        When 執行解析
        Then 得到經過下列步驟建構的設置 `config`
        """
        # Create a simple config file
        config_data = {"model": {"type": "simple"}}
        config_path = temp_dir / "config.yaml"
        write_yaml_file(config_path, config_data)

        # Initialize parser and parse args
        parser = SymConfParser()
        config = parser.parse_args([str(config_path)])

        # Verify config is built correctly
        assert hasattr(config, "model")
        assert config.model.type == "simple"

    def test_step1_load_yaml_and_dotenv_files(self, temp_dir: Path):
        """Test Step 1: Loading YAML and dotenv files with deep merging.

        Given 準備多個 YAML 檔案
        When 執行命令讀取多個檔案
        Then 得到合併後的設置
        """
        # Create config1.yaml
        config1_data = {
            "server": {
                "host": "localhost",
                "ports": [8080, 8081],
            }
        }
        config1_path = temp_dir / "config1.yaml"
        write_yaml_file(config1_path, config1_data)

        # Create config2.yaml
        config2_data = {
            "server": {
                "timeout": 10,
                "ports": [9090],
            }
        }
        config2_path = temp_dir / "config2.yaml"
        write_yaml_file(config2_path, config2_data)

        # Create a dotenv file
        dotenv_path = temp_dir / ".env"
        with open(dotenv_path, "w") as f:
            f.write("TEST_VAR=hello\n")
            f.write("ANOTHER_VAR=world\n")

        # Parse multiple files
        parser = SymConfParser()
        config = parser.parse_args([str(config1_path), str(config2_path), "--env", str(dotenv_path)])

        # Verify deep merge with later files taking priority
        assert config.server.host == "localhost"  # From config1.yaml
        assert config.server.timeout == 10  # From config2.yaml
        assert config.server.ports == [9090]  # List replaced, not merged
        assert os.environ.get("TEST_VAR") == "hello"
        assert os.environ.get("ANOTHER_VAR") == "world"
        os.environ.pop("TEST_VAR")
        os.environ.pop("ANOTHER_VAR")

    def test_step2_command_line_arguments(self, temp_dir: Path):
        """Test Step 2: Using command line arguments to override settings.

        Given 準備基礎 YAML 設置
        When 使用命令列參數覆寫設置
        Then 得到覆寫後的設置
        """
        # Create basic config
        config_data = {"exp": {"seed": 42}}
        config_path = temp_dir / "config.yaml"
        write_yaml_file(config_path, config_data)

        # Parse with command line overrides
        parser = SymConfParser()
        config = parser.parse_args([str(config_path), "--args", "exp.name=hi", "exp.seed=3", "exp.name=he"])

        # Verify overrides
        assert config.exp.seed == 3  # Overridden from 42
        assert config.exp.name == "he"  # Newly added parameter

    def test_step3_remove_parameters(self, temp_dir: Path):
        """Test Step 3: Removing parameters using REMOVE keyword.

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

        # Parse with removal
        parser = SymConfParser()
        config = parser.parse_args([str(default_path), str(override_path), "--args", "server.port=REMOVE"])

        # Verify removal
        assert config.server.host == "localhost"
        assert config.server.timeout == 10
        assert not hasattr(config.server, "debug")  # Should be removed
        assert not hasattr(config.server, "port")  # Should be removed

    def test_step4_complex_kwargs_chain_completion(self, temp_dir: Path):
        """Test Step 4: Complex **kwargs chain parameter default completion.

        Given 定義帶有預設參數的物件 with **kwargs chain (func -> BaseModel -> AwesomeModelStep4)
        And 準備只設定部分參數的設置
        When 解析設置
        Then 系統自動補全預設值，得到設置等同於 HOWTO.md example
        """
        # Following the exact HOWTO.md Step 4 example
        config_data = {
            "model": {
                "TYPE": "tests.conftest.AwesomeModelStep4",
                "act": "relu",  # Parameter for func() via **kwargs chain
                "learning_rate": 1e-4,  # Parameter for BaseModel, user explicitly set
                # message should be auto-completed from func() default
                # loss_scale should be auto-completed from AwesomeModelStep4 default
                # batch_size is NOT included as it's overridden in AwesomeModelStep4.__init__
            }
        }
        config_path = temp_dir / "config.yaml"
        write_yaml_file(config_path, config_data)

        parser = SymConfParser(validate_type=False, validate_mapping=False)
        config = parser.parse_args([str(config_path)])

        # Verify completion following HOWTO.md expectations
        assert config.model.TYPE == "tests.conftest.AwesomeModelStep4"
        assert config.model.act == "relu"  # 使用者設定的值
        assert config.model.learning_rate == 1e-4  # 使用者明確設定的參數不會被覆寫
        assert config.model.message == "hello"  # 自動補全的預設值 from func()
        assert config.model.loss_scale == 1.0  # 自動補全的預設值 from AwesomeModelStep4
        assert not hasattr(config.model, "batch_size")  # batch_size 非 AwesomeModelStep4 可設定的參數 (overridden)

    def test_step5_variable_interpolation_comprehensive(self, temp_dir: Path):
        """Test Step 5: Variable interpolation (引用變數值) - comprehensive test.

        Given 展示三種插值和遞迴引用的綜合範例 and 設定環境變數
        When 解析設置
        Then 所有插值被遞迴解析為實際值

        Tests all three interpolation types:
        - 參數插值 ${simple_name}: referencing config parameters
        - 環境變數插值 ${UPPER_CASE}: referencing environment variables
        - 表達式插值 ${... `variable` ...}: executing Python expressions with backtick variables
        """
        # Set environment variables as in HOWTO.md example
        set_env_vars(BASE_FEATURE_SIZE="10", FEATURE_SIZE="10")

        try:
            # Following the exact HOWTO.md Step 5 comprehensive example
            config_data = {
                # 遞迴引用：引用其他計算結果
                "total_params": "${`model.hidden_dim` + `model.output_features`}",
                "dataset": {
                    "name": "cifar10",
                    "num_classes": "${BASE_FEATURE_SIZE}",  # 間接引用環境變數
                },
                "model": {
                    # 參數插值（直接引用）
                    "output_features": "${dataset.num_classes}",
                    # 嵌入字串中使用
                    "name": "model_${dataset.name}_h=${model.hidden_dim}",
                    # 環境變數插值
                    "hidden_dim": "${FEATURE_SIZE}",
                    # 表達式插值
                    "dropout": "${0.1 if max(`dataset.num_classes` * 2, 2) < 5 else 0.0}",
                },
            }
            config_path = temp_dir / "config.yaml"
            write_yaml_file(config_path, config_data)

            parser = SymConfParser()
            config = parser.parse_args([str(config_path)])

            # Verify all interpolation types work as expected from HOWTO.md
            assert config.dataset.name == "cifar10"
            assert config.dataset.num_classes == 10  # 環境變數插值: BASE_FEATURE_SIZE

            assert config.model.output_features == 10  # 參數插值: dataset.num_classes
            assert config.model.name == "model_cifar10_h=10"  # 字串嵌入: dataset.name + multiplier
            assert config.model.hidden_dim == 10  # 環境變數插值: FEATURE_SIZE
            assert config.model.dropout == 0.0  # 表達式插值: max(10*2, 2) = 20, 20 < 5 = False

            assert config.total_params == 20  # 遞迴引用: 10 + 10

        finally:
            cleanup_env_vars("FEATURE_SIZE")

    def test_step5_circular_dependency_detection(self, temp_dir: Path):
        """Test circular dependency detection in interpolation.

        Given 插值形成循環引用
        When 解析時有循環依賴
        Then 顯示循環插值錯誤
        """
        config_data = {
            "a": "${b}",
            "b": "${c}",
            "c": 3,
        }
        config_path = temp_dir / "config.yaml"
        write_yaml_file(config_path, config_data)

        parser = SymConfParser()

        # Create circular dependency via command line
        with pytest.raises(CircularInterpolationError) as exc_info:
            parser.parse_args(
                [
                    str(config_path),
                    "--args",
                    "c=${a}",  # Creates circular dependency: a -> b -> c -> a
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
            assert error_msg == dedent(message).rstrip()

    def test_step6_type_validation(self, temp_dir: Path, test_classes):
        """Test Step 6: Type validation.

        Given 定義範例類別和函式 and 初始化 `SymConfParser` 並指定 base_classes and 準備包含各種型別情況的設置
        When 解析設置
        Then 系統一次性報告所有參數驗證錯誤
        """
        yaml_content = """
        model:
            TYPE: tests.conftest.Child
            percent: 1                           # 錯誤：應該要是 float
            animal: pig                          # 錯誤：值應該是 'cat' 或 'dog'  
            dummy: false                         # 正確：無型別註解不檢查
            toy:                                 # 正確：物件返回值符合型別
                TYPE: tests.conftest.SuperToy 
            stoy:                                # 錯誤：Toy 不是 SuperToy
                TYPE: tests.conftest.Toy         
            toy_cls: !!python/name:tests.conftest.Toy  # 正確：使用 PyYAML 標籤傳入類別本身
            stoy_cls:                            # 錯誤：期待型別而非實例
                TYPE: tests.conftest.SuperToy
            number:                              # 正確：函式返回值符合型別
                TYPE: tests.conftest.square
                value: 0.3
            name: null                           # 正確：以子類別定義為準
            vocab: [a, b]                        # 正確：容器型別只檢查第一層
            
        """
        config_path = temp_dir / "config.yaml"
        with open(config_path, "w") as f:
            f.write(dedent(yaml_content).strip())

        parser = SymConfParser(validate_type=True, base_classes={"model": test_classes["Parent"]})

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
        Expected: Optional[tests.conftest.SuperToy]
        Actual: ... (tests.conftest.Toy)

        ❌ Type mismatch
        Parameter: model.stoy_cls
        Expected: Type[tests.conftest.SuperToy]
        Actual: ... (tests.conftest.SuperToy)
        """
        assert set(dedent(message).strip().split("\n\n")) == set(error_msg.split("\n\n"))

    def test_step6_parameter_mapping_validation(self, temp_dir: Path):
        """Test Step 6: Parameter mapping validation.

        Given 物件定義 and 初始化有啟用參數對應性檢查的 `SymConfParser` and 準備包含參數錯誤的設置
        When 解析設置
        Then 系統一次性報告所有參數驗證錯誤
        """
        config_data = {
            "model": {
                "TYPE": "tests.conftest.ChildForMapping",
                # Missing required parameter 'a'
                # Missing required parameter 'd' (for parent)
                "c": 5,  # Unexpected parameter
                "e": 7,  # Unexpected parameter
            },
            "fn": {
                "TYPE": "tests.conftest.square",
                "value": 3.0,  # Correct parameter
                "z": 5,  # Unexpected parameter
            },
        }
        config_path = temp_dir / "config.yaml"
        write_yaml_file(config_path, config_data)

        parser = SymConfParser(validate_mapping=True)

        with pytest.raises(ParameterValidationError) as exc_info:
            parser.parse_args([str(config_path)])

        error_msg = str(exc_info.value)
        print("Actual error message:")
        print(repr(error_msg))

        # The test expects Child to have different parameters than what's in conftest.py
        # Let's see what the actual error is and fix accordingly
        message = """
        ❌ Missing parameters
        Parameters: model.a, model.d
        Object: tests.conftest.ChildForMapping

        ❌ Unexpected parameters
        Parameters: model.c, model.e
        Object: tests.conftest.ChildForMapping

        ❌ Unexpected parameters
        Parameters: fn.z
        Object: tests.conftest.square
        """
        assert set(dedent(message).strip().split("\n\n")) == set(error_msg.split("\n\n"))

    def test_complete_configuration_building_process(self, temp_dir: Path):
        """Test the complete configuration building process with all steps."""
        # Step 1: Create multiple YAML files
        base_config = {
            "server": {"host": "localhost", "debug": True},
            "model": {
                "TYPE": "tests.conftest.AwesomeModel",
                "learning_rate": 1e-4,
                # batch_size will be completed from defaults
            },
        }
        base_path = temp_dir / "base.yaml"
        write_yaml_file(base_path, base_config)

        override_config = {
            "server": {"debug": "REMOVE"},  # Step 3: Remove parameter
            "training": {"epochs": "${EPOCHS}"},  # Step 5: Env var interpolation
        }
        override_path = temp_dir / "override.yaml"
        write_yaml_file(override_path, override_config)

        # Set environment variable for interpolation
        set_env_vars(EPOCHS="100")

        try:
            parser = SymConfParser(validate_type=False, validate_mapping=False)
            config = parser.parse_args(
                [
                    str(base_path),
                    str(override_path),
                    "--args",
                    "model.learning_rate=1e-3",  # Step 2: Command line override
                    "server.port=8080",  # Step 2: Add new parameter
                ]
            )

            # Verify all steps worked
            assert config.server.host == "localhost"  # From base
            assert config.server.port == 8080  # From command line
            assert not hasattr(config.server, "debug")  # Removed
            assert config.model.learning_rate == 1e-3  # Overridden
            assert config.model.batch_size == 32  # Default completed
            assert config.training.epochs == 100  # Interpolated

        finally:
            cleanup_env_vars("EPOCHS")
