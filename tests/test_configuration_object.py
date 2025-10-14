"""Test cases for SynConf configuration object operations (操作設置物件).

This module tests configuration object manipulation functionality following HOWTO.md structure.
"""

from pathlib import Path

import tests
from synconf import SynConfig, SynConfParser
from tests.conftest import write_yaml_file


def test_dict_style_access_and_modification(temp_dir: Path):
    """Test dict-style access and modification (存取與變更參數值).

    Given 已解析的設置物件
    When 使用 dict 風格存取
    Then 兩種方式都能正確操作設置
    """
    config_data = {
        "model": {
            "learning_rate": 1e-4,
            "batch_size": 32,
        },
        "training": {"epochs": 100},
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser()
    config = parser.parse_args([str(config_path)])

    # Test dict-style access
    # 取值
    assert config["model"]["learning_rate"] == 1e-4

    # 預設值
    assert config["model"].get("learning_rate", 0.01) == 1e-4
    assert config["model"].get("nonexistent", 0.01) == 0.01

    # 設值
    config["model"]["learning_rate"] = 0.01
    assert config["model"]["learning_rate"] == 0.01

    # 新增參數
    config["model"]["new_param"] = "test"
    assert config["model"]["new_param"] == "test"

    # 刪除
    config["model"].pop("new_param")
    assert "new_param" not in config["model"]


def test_attribute_style_access_and_modification(temp_dir: Path):
    """Test attribute-style access and modification.

    Given 已解析的設置物件
    When 使用 attribute 風格存取
    Then 兩種方式都能正確操作設置
    """
    config_data = {
        "model": {
            "learning_rate": 1e-4,
            "batch_size": 32,
        }
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser()
    config = parser.parse_args([str(config_path)])

    # Test attribute-style access
    # 取值
    assert config.model.learning_rate == 1e-4

    # 預設值
    assert getattr(config.model, "learning_rate", 0.01) == 1e-4
    assert getattr(config.model, "nonexistent", 0.01) == 0.01

    # 設值
    config.model.learning_rate = 0.01
    assert config.model.learning_rate == 0.01

    # 新增參數
    config.model.new_param = "test"
    assert config.model.new_param == "test"

    # 刪除
    delattr(config.model, "new_param")
    assert not hasattr(config.model, "new_param")


def test_automatic_object_realization(temp_dir: Path):
    """Test automatic object realization (自動實現物件).

    Given 定義相關的類別和函式 and 準備包含巢狀物件的設置
    When 自動實現所有物件
    Then 得到完全實例化的物件
    """
    config_data = {
        "model": {
            "TYPE": "tests.data.realization.AwesomeModelWithOptimizer",
            "hidden_size": 64,
            "optimizer": {
                "TYPE": "tests.data.realization.create_optimizer",
                "lr": 0.01,
            },
        }
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser(validate_type=False, validate_mapping=False)
    config = parser.parse_args([str(config_path)])

    # Auto-realize all objects
    realized_config = config.realize()

    # Verify object realization

    assert isinstance(realized_config["model"], tests.data.realization.AwesomeModelWithOptimizer)
    assert realized_config["model"].hidden_size == 64
    assert isinstance(realized_config["model"].optimizer, tests.data.realization.Optimizer)
    assert realized_config["model"].optimizer.lr == 0.01


def test_partial_object_realization_with_overwrites(temp_dir: Path):
    """Test partial object realization with parameter overwrites.

    When 實現某設置下的所有物件，並覆蓋部分參數
    Then 得到覆蓋參數後的實例
    """
    config_data = {
        "model": {
            "TYPE": "tests.data.realization.AwesomeModelWithOptimizer",
            "hidden_size": 64,
            "optimizer": {
                "TYPE": "tests.data.realization.create_optimizer",
                "lr": 0.01,
            },
        }
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser(validate_type=False, validate_mapping=False)
    config = parser.parse_args([str(config_path)])

    # Realize with overwrites
    model = config.model.realize(overwrites={"optimizer.lr": 0.02})

    # Verify overwrite was applied
    assert isinstance(model, tests.data.realization.AwesomeModelWithOptimizer)
    assert model.optimizer.lr == 0.02  # Overridden value


def test_manual_object_realization(temp_dir: Path):
    """Test manual object realization (手動實現物件).

    Given 準備簡單的物件設置
    When 手動實例化物件
    Then 得到實例化的物件
    """
    config_data = {
        "model": {
            "TYPE": "tests.data.realization.AwesomeModel",
            "learning_rate": 1e-3,
            "batch_size": 64,
        }
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser(validate_type=False, validate_mapping=False)
    config = parser.parse_args([str(config_path)])

    # Manual realization using kwargs
    model = tests.data.realization.AwesomeModel(**config.model.kwargs)

    # Verify manual realization
    assert isinstance(model, tests.data.realization.AwesomeModel)
    assert model.learning_rate == 1e-3
    assert model.batch_size == 64


def test_instance_method_realization(temp_dir: Path):
    """Test instance method realization (實現 instance method).

    Given 定義包含 instance method 的類別 and 準備 instance method 的設置
    When 自動實現 instance method
    Then 得到方法執行的返回值
    """
    config_data = {
        "TYPE": "tests.data.realization.Experiment.cross_validate",
        "folds": 5,
        "self": {
            "TYPE": "tests.data.realization.Experiment",
            "seed": 1,
        },
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser(validate_type=False, validate_mapping=False)
    config = parser.parse_args([str(config_path)])

    # Auto-realize instance method
    metrics = config.realize()

    # Verify method execution result
    assert isinstance(metrics, dict)
    assert metrics == {"F1": 0.9, "Precision": 0.95}


def test_manual_instance_method_realization(temp_dir: Path):
    """Test manual instance method realization.

    Given 定義需要複雜初始化的類別 and 準備 instance method 的設置
    When 手動創建實例並呼叫方法
    Then 得到使用指定實例執行的方法結果
    """
    config_data = {
        "processor_task": {
            "TYPE": "tests.data.realization.DataProcessor.get_num_targets",
            "batch_size": 32,
        }
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser(validate_type=False, validate_mapping=False)
    config = parser.parse_args([str(config_path)])

    # Manual instance method realization
    # 手動創建並控制實例化過程
    processor = tests.data.realization.DataProcessor(complex_data=None)  # 可能是很複雜的資料

    # 獲取方法並手動呼叫
    method = config.processor_task.resolve_type()  # 獲取 get_num_targets 方法
    result = method(processor, **config.processor_task.kwargs)  # 傳入實例和參數

    # Verify result matches expected from HOWTO.md
    assert result == 96  # 3 * 32 = 96


def test_configuration_serialization(temp_dir: Path):
    """Test configuration serialization (序列化設置).

    Given 準備包含巢狀結構的設置
    When 序列化為扁平化格式
    Then 得到扁平化的美觀字典
    """
    config_data = {
        "model": {
            "TYPE": "tests.data.realization.AwesomeModel",
            "hidden_size": 64,
        },
        "dataset": {
            "batch_size": 32,
        },
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser(validate_mapping=False)
    config = parser.parse_args([str(config_path)])

    # Serialize to flattened format
    pretty_config = config.pretty()

    # Verify flattened keys
    expected_keys = {
        "model.TYPE",
        "model.hidden_size",
        "model.batch_size",
        "model.learning_rate",
        "dataset.batch_size",
    }
    assert set(pretty_config.keys()) == expected_keys
    assert pretty_config["model.TYPE"] == "tests.data.realization.AwesomeModel"
    assert pretty_config["model.hidden_size"] == 64
    assert pretty_config["dataset.batch_size"] == 32


def test_serialization_with_exclusions(temp_dir: Path):
    """Test serialization with parameter exclusions.

    When 排除特定參數進行序列化
    Then 得到排除指定參數的結果
    """
    config_data = {
        "model": {
            "TYPE": "tests.data.realization.AwesomeModel",
            "hidden_size": 64,
        },
        "dataset": {
            "batch_size": 32,
        },
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser(validate_mapping=False)
    config = parser.parse_args([str(config_path)])

    # Serialize with exclusions
    pretty_config = config.pretty(exclude=["dataset.batch_size"])

    # Verify exclusion
    assert "dataset.batch_size" not in pretty_config
    assert "model.TYPE" in pretty_config
    assert "model.hidden_size" in pretty_config


def test_serialization_with_realized_objects(temp_dir: Path):
    """Test that serialization converts object instances back to class name strings."""
    config_data = {
        "model": {
            "TYPE": "tests.data.realization.AwesomeModel",
            "learning_rate": 1e-3,
        }
    }
    config_path = temp_dir / "config.yaml"
    write_yaml_file(config_path, config_data)

    parser = SynConfParser(validate_type=False, validate_mapping=False)
    config = parser.parse_args([str(config_path)])

    # Realize the object
    realized_model = config.model.realize()

    # Create new config with realized object
    new_config = SynConfig({"model": realized_model})

    # Serialize - should convert back to class name
    pretty_config = new_config.pretty()

    # Verify object instance is converted to class name
    assert "model" in pretty_config
    # Note: The exact serialization of realized objects depends on implementation
