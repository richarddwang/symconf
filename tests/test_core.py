"""Core test module for SymConf functionality."""

import os
import tempfile

import pytest
import yaml

# Import the SymConf components
from symconf import SymConfParser
from symconf.exceptions import CircularInterpolationError, ParameterValidationError


class TestBasicConfigurationLoading:
    """Test basic configuration loading functionality from HOWTO.md Step 1."""

    def test_single_yaml_file_loading(self):
        """Test loading a single YAML file."""
        # This test will be implemented once SymConfParser exists
        pytest.skip("SymConfParser not implemented yet")

        # Expected implementation:
        # parser = SymConfParser()
        # config = parser.parse_args(['tests/data/config1.yaml'])
        # assert config['server']['host'] == 'localhost'
        # assert config['server']['ports'] == [8080, 8081]

    def test_multiple_yaml_files_deep_merge(self):
        """Test deep merging of multiple YAML files with later files taking precedence."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior from HOWTO.md:
        # parser = SymConfParser()
        # config = parser.parse_args(['tests/data/config1.yaml', 'tests/data/config2.yaml'])
        #
        # assert config['server']['host'] == 'localhost'  # from config1
        # assert config['server']['timeout'] == 10        # from config2
        # assert config['server']['ports'] == [9090]      # list replaced by config2

    def test_dotenv_file_loading(self):
        """Test loading dotenv files with --env parameter."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior:
        # parser = SymConfParser()
        # config = parser.parse_args(['tests/data/config_interpolation.yaml', '--env', 'tests/data/test.env'])
        # # Environment variables should be available for interpolation


class TestCommandLineArguments:
    """Test command line argument functionality from HOWTO.md Step 2."""

    def test_args_parameter_override(self):
        """Test overriding parameters with --args using dot notation."""

        parser = SymConfParser(validate_type=False, validate_mapping=False)
        config = parser.parse_args(
            ["tests/data/config1.yaml", "--args", "server.host=example.com", "server.timeout=30"]
        )

        assert config["server"]["host"] == "example.com"  # overridden
        assert config["server"]["timeout"] == 30  # added
        assert config["server"]["ports"] == [8080, 8081]  # preserved

    def test_args_parameter_precedence(self):
        """Test that later --args parameters take precedence."""

        parser = SymConfParser(validate_type=False, validate_mapping=False)
        config = parser.parse_args(
            ["tests/data/config1.yaml", "--args", "server.host=first.com", "server.host=second.com"]
        )

        assert config["server"]["host"] == "second.com"  # later args win


class TestParameterRemoval:
    """Test parameter removal functionality from HOWTO.md Step 3."""

    def test_remove_keyword_in_yaml(self):
        """Test using REMOVE keyword in YAML files."""
        pytest.skip("SymConfParser not implemented yet")

        # Create temporary config files for test
        # with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f1:
        #     yaml.dump({'server': {'host': 'localhost', 'debug': True, 'port': 9090}}, f1)
        #     config1_path = f1.name
        #
        # with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f2:
        #     yaml.dump({'server': {'debug': 'REMOVE'}}, f2)
        #     config2_path = f2.name
        #
        # try:
        #     parser = SymConfParser()
        #     config = parser.parse_args([config1_path, config2_path])
        #
        #     assert config['server']['host'] == 'localhost'  # preserved
        #     assert config['server']['port'] == 9090         # preserved
        #     assert 'debug' not in config['server']          # removed
        # finally:
        #     os.unlink(config1_path)
        #     os.unlink(config2_path)

    def test_remove_keyword_in_args(self):
        """Test using REMOVE keyword in command line arguments."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior:
        # parser = SymConfParser()
        # config = parser.parse_args([
        #     'tests/data/config1.yaml',
        #     '--args', 'server.ports=REMOVE'
        # ])
        #
        # assert config['server']['host'] == 'localhost'  # preserved
        # assert 'ports' not in config['server']          # removed


class TestDefaultValueCompletion:
    """Test default value completion from HOWTO.md Step 4."""

    def test_object_default_value_completion(self):
        """Test automatic completion of object parameter defaults."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior:
        # with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        #     yaml.dump({
        #         'model': {
        #             'TYPE': 'tests.test_objects.AwesomeModel',
        #             'learning_rate': 1e-3
        #             # batch_size not set, but has default value
        #         }
        #     }, f)
        #     config_path = f.name
        #
        # try:
        #     parser = SymConfParser()
        #     config = parser.parse_args([config_path])
        #
        #     assert config['model']['learning_rate'] == 1e-3  # user set
        #     assert config['model']['hidden_size'] == 32      # auto-completed default
        # finally:
        #     os.unlink(config_path)

    def test_only_type_objects_get_defaults(self):
        """Test that only objects with TYPE get default completion."""
        pytest.skip("SymConfParser not implemented yet")

        # Objects without TYPE should not get default completion

    def test_import_error_reporting(self):
        """Test that import errors are properly reported, not silently ignored."""
        pytest.skip("SymConfParser not implemented yet")

        # This test ensures import errors are not suppressed in _complete_default_values
        # with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        #     yaml.dump({
        #         'model': {
        #             'TYPE': 'nonexistent.module.NonexistentClass',
        #             'param1': 'value1'
        #         }
        #     }, f)
        #     config_path = f.name
        #
        # try:
        #     parser = SymConfParser()
        #
        #     # Should raise ImportError, not silently ignore
        #     with pytest.raises(ImportError, match="Cannot import nonexistent.module.NonexistentClass"):
        #         config = parser.parse_args([config_path])
        # finally:
        #     os.unlink(config_path)

    def test_import_error_detailed_message(self):
        """Test that import errors provide detailed error messages."""
        pytest.skip("SymConfParser not implemented yet")

        # Test various import error scenarios
        # test_cases = [
        #     {
        #         'TYPE': 'nonexistent_module.SomeClass',
        #         'expected_error': 'Cannot import nonexistent_module.SomeClass'
        #     },
        #     {
        #         'TYPE': 'os.NonexistentClass',
        #         'expected_error': 'Cannot import os.NonexistentClass'
        #     }
        # ]
        #
        # for case in test_cases:
        #     with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        #         yaml.dump({
        #             'obj': {
        #                 'TYPE': case['TYPE'],
        #                 'param': 'value'
        #             }
        #         }, f)
        #         config_path = f.name
        #
        #     try:
        #         parser = SymConfParser()
        #         with pytest.raises(ImportError, match=case['expected_error']):
        #             config = parser.parse_args([config_path])
        #     finally:
        #         os.unlink(config_path)


class TestVariableInterpolation:
    """Test variable interpolation from HOWTO.md Step 5."""

    def test_parameter_interpolation(self):
        """Test parameter interpolation ${param.path}."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"dataset": {"num_classes": 10}, "model": {"output_features": "${dataset.num_classes}"}}, f)
            config_path = f.name

        try:
            parser = SymConfParser()
            config = parser.parse_args([config_path])

            assert config["model"]["output_features"] == 10
        finally:
            os.unlink(config_path)

    def test_environment_variable_interpolation(self):
        """Test environment variable interpolation ${ENV_VAR}."""
        # Set environment variable for test
        os.environ["TEST_FEATURE_SIZE"] = "64"

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump({"model": {"hidden_dim": "${TEST_FEATURE_SIZE}"}}, f)
                config_path = f.name

            try:
                parser = SymConfParser()
                config = parser.parse_args([config_path])

                assert config["model"]["hidden_dim"] == 64
            finally:
                os.unlink(config_path)
        finally:
            del os.environ["TEST_FEATURE_SIZE"]

    def test_dotenv_updates_global_environment(self):
        """Test that loading dotenv files updates os.environ globally."""
        # This test ensures dotenv variables are available globally
        old_env_value = os.environ.get("TEST_DOTENV_VAR")

        try:
            # Create temporary dotenv file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
                f.write("TEST_DOTENV_VAR=dotenv_value\n")
                env_path = f.name

            # Create config that uses environment interpolation
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump({"test_param": "${TEST_DOTENV_VAR}"}, f)
                config_path = f.name

            try:
                parser = SymConfParser()
                config = parser.parse_args([config_path, "--env", env_path])

                # Verify the value is interpolated correctly
                assert config["test_param"] == "dotenv_value"

                # Verify the environment variable is globally available
                assert os.environ["TEST_DOTENV_VAR"] == "dotenv_value"

            finally:
                os.unlink(config_path)
                os.unlink(env_path)
        finally:
            if old_env_value is None:
                os.environ.pop("TEST_DOTENV_VAR", None)
            else:
                os.environ["TEST_DOTENV_VAR"] = old_env_value

    def test_interpolation_engine_uses_global_environment(self):
        """Test that InterpolationEngine can access global environment variables."""
        # This test verifies InterpolationEngine doesn't need explicit env_vars
        old_value = os.environ.get("TEST_GLOBAL_ENV")

        try:
            os.environ["TEST_GLOBAL_ENV"] = "global_value"

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump({"param": "${TEST_GLOBAL_ENV}"}, f)
                config_path = f.name

            try:
                parser = SymConfParser()
                config = parser.parse_args([config_path])

                assert config["param"] == "global_value"
            finally:
                os.unlink(config_path)
        finally:
            if old_value is None:
                os.environ.pop("TEST_GLOBAL_ENV", None)
            else:
                os.environ["TEST_GLOBAL_ENV"] = old_value

    def test_expression_interpolation(self):
        """Test expression interpolation with backticks."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "dataset": {"num_classes": 10},
                    "model": {"dropout": "${0.1 if max(`dataset.num_classes` * 2, 2) < 5 else 0.0}"},
                },
                f,
            )
            config_path = f.name

        try:
            parser = SymConfParser()
            config = parser.parse_args([config_path])

            # max(10 * 2, 2) = 20, 20 < 5 = False, so should be 0.0
            assert config["model"]["dropout"] == 0.0
        finally:
            os.unlink(config_path)

    def test_string_embedding_interpolation(self):
        """Test interpolation embedded in strings."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"dataset": {"name": "cifar10"}, "model": {"name": "model_${dataset.name}_v2"}}, f)
            config_path = f.name

        try:
            parser = SymConfParser()
            config = parser.parse_args([config_path])

            assert config["model"]["name"] == "model_cifar10_v2"
        finally:
            os.unlink(config_path)

    def test_circular_dependency_detection(self):
        """Test circular dependency detection in interpolation."""
        circular_config = {"a": "${b}", "b": "${c}", "c": "3"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(circular_config, f)
            config_path = f.name

        try:
            parser = SymConfParser()
            # Create circular dependency via CLI args
            with pytest.raises(CircularInterpolationError) as exc_info:
                config = parser.parse_args([config_path, "--args", "c=${a}"])

            # Check that error message contains cycle information
            error_msg = str(exc_info.value)
            assert "a" in error_msg and "b" in error_msg and "c" in error_msg
        finally:
            os.unlink(config_path)


class TestConfigurationValidation:
    """Test configuration validation from HOWTO.md Step 6."""

    def test_type_validation_enabled(self, temp_dir):
        """Test type validation when enabled."""

        config_path = temp_dir / "config.yaml"
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.TestModel",
                "learning_rate": 1,  # Should be float - will cause type error
                "batch_size": "invalid",  # Should be int - will cause type error
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        parser = SymConfParser(validate_type=True, validate_mapping=True)

        with pytest.raises(ParameterValidationError) as exc_info:
            parser.parse_args([str(config_path)])

        # Check that type validation errors are reported
        error_str = str(exc_info.value)
        assert "Type mismatch" in error_str
        assert "learning_rate" in error_str
        assert "batch_size" in error_str

    def test_type_validation_literal_values(self, temp_dir):
        """Test validation of Literal type values."""

        config_path = temp_dir / "config.yaml"
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.ChildClass",
                "percent": 0.5,  # Valid float
                "animal": "pig",  # Invalid literal value - should be 'cat' or 'dog'
                "b": True,  # Valid bool for parent
                "e": "elephant",  # Valid value for AClass.create
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        parser = SymConfParser(validate_type=True, validate_mapping=True)

        with pytest.raises(ParameterValidationError) as exc_info:
            parser.parse_args([str(config_path)])

        # Check that literal validation error is reported
        error_str = str(exc_info.value)
        assert "Value not in allowed range" in error_str or "not in allowed" in error_str
        assert "animal" in error_str
        assert "'pig'" in error_str

    def test_type_validation_union_types(self, temp_dir):
        """Test validation of Union types."""

        config_path = temp_dir / "config.yaml"
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.Parent",
                "name": "test",  # Valid str
                "number": 42,  # Valid int (Union[int, float])
                "vocab": [1.0, 2.0],  # Valid list[float]
                "toy": None,  # Valid None (Union[str, None])
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        parser = SymConfParser(validate_type=True, validate_mapping=True)

        # This should NOT raise an error since all types are valid
        config = parser.parse_args([str(config_path)])
        assert config.model.name == "test"
        assert config.model.number == 42

    def test_parameter_mapping_validation(self, temp_dir):
        """Test parameter mapping validation."""

        config_path = temp_dir / "config.yaml"
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.ChildClass",
                "parcent": 0.1,  # Typo: should be 'percent' - unexpected parameter
                # Missing required parameter 'percent'
                "b": True,
                "e": "elephant",
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        parser = SymConfParser(validate_type=True, validate_mapping=True)

        with pytest.raises(ParameterValidationError) as exc_info:
            parser.parse_args([str(config_path)])

        # Check that mapping validation errors are reported
        error_str = str(exc_info.value)
        assert "Unexpected parameter" in error_str or "Missing parameter" in error_str

    def test_validation_with_kwargs_tracing(self, temp_dir):
        """Test that validation works with **kwargs parameter tracing."""

        config_path = temp_dir / "config.yaml"
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.ChildClass",
                "percent": 0.8,  # ChildClass parameter
                "b": True,  # Parent parameter (via **kwargs)
                "e": "elephant",  # AClass.create parameter (via **kwargs)
                "f": 10,  # func parameter (via **kwargs)
                "g": 2.5,  # BClass.my_method parameter (via **kwargs)
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        parser = SymConfParser(validate_type=True, validate_mapping=True)

        # This should NOT raise an error since all parameters are valid
        # and traced through the **kwargs chain
        config = parser.parse_args([str(config_path)])
        assert config.model.percent == 0.8
        assert config.model.g == 2.5  # Parameter from deep in kwargs chain

    def test_validation_error_message_format(self, temp_dir):
        """Test that validation error messages match HOWTO.md format."""

        config_path = temp_dir / "config.yaml"
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.ChildClass",
                "percent": 1,  # Type error: int instead of float
                "animal": "pig",  # Literal error: invalid value
                "b": True,
                "e": "elephant",
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        parser = SymConfParser(validate_type=True, validate_mapping=True)

        with pytest.raises(ParameterValidationError) as exc_info:
            parser.parse_args([str(config_path)])

        # Check error message format matches HOWTO.md specification
        error_str = str(exc_info.value)

        # Should contain parameter path and type information
        assert "model.percent" in error_str
        assert "model.animal" in error_str

        # Should contain actual and expected type information
        assert "int" in error_str  # actual type
        assert "float" in error_str  # expected type


class TestHelpFunctionality:
    """Test help functionality from HOWTO.md."""

    def test_print_complete_configuration(self):
        """Test --print parameter shows complete configuration."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior:
        # --print should display final configuration in YAML format
        # and wait for user confirmation

    def test_object_parameter_inspection(self):
        """Test --help.object parameter inspection."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior:
        # --help.object=tests.test_objects.Child should show all parameters
        # including inherited and **kwargs parameters


class TestConfigurationObjectOperations:
    """Test configuration object operations from HOWTO.md."""

    def test_dict_style_access(self):
        """Test dictionary-style access to configuration."""
        pytest.skip("SymConfConfig not implemented yet")

        # Expected behavior:
        # config['model']['learning_rate']  # get
        # config['model']['learning_rate'] = 0.01  # set
        # config['model'].pop('learning_rate')  # delete

    def test_attribute_style_access(self):
        """Test attribute-style access to configuration."""
        pytest.skip("SymConfConfig not implemented yet")

        # Expected behavior:
        # config.model.learning_rate  # get
        # config.model.learning_rate = 0.01  # set
        # delattr(config.model, 'learning_rate')  # delete

    def test_automatic_object_realization(self):
        """Test automatic object realization with realize() method."""
        pytest.skip("SymConfConfig not implemented yet")

        # Expected behavior:
        # config.realize() should recursively instantiate all TYPE objects
        # config.model.realize(overwrites={'optimizer.lr': 0.02}) should allow overrides

    def test_manual_object_realization(self):
        """Test manual object realization with kwargs property."""
        pytest.skip("SymConfConfig not implemented yet")

        # Expected behavior:
        # config.model.kwargs should return filtered parameters (no TYPE, CLASS)
        # AwesomeModel(**config.model.kwargs) should work

    def test_instance_method_realization(self):
        """Test instance method realization with CLASS keyword."""
        pytest.skip("SymConfConfig not implemented yet")

        # Expected behavior:
        # TYPE: Experiment.cross_validate with CLASS: {seed: 1}
        # should create instance and call method

    def test_configuration_serialization(self):
        """Test configuration serialization with pretty() method."""
        pytest.skip("SymConfConfig not implemented yet")

        # Expected behavior:
        # config.pretty() should return flattened dict with dot notation
        # config.pretty(exclude=['dataset.batch_size']) should exclude parameters


class TestListManipulation:
    """Test LIST type functionality from HOWTO.md."""

    def test_list_type_processing(self):
        """Test TYPE: LIST allows dict-style list manipulation."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior:
        # TYPE: LIST with named keys should convert to regular list
        # REMOVE values should be excluded

    def test_list_type_merging(self):
        """Test LIST type merging across multiple files."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior from HOWTO.md:
        # default.yaml with callbacks, override.yaml with REMOVE and additions
        # should merge correctly


class TestParameterSweeping:
    """Test parameter sweeping functionality from HOWTO.md."""

    def test_manual_parameter_iteration(self):
        """Test manual parameter iteration in user code."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior:
        # Multiple calls to parse_args with different --args should work
        # All interpolation and merging logic should be preserved

    def test_simple_parameter_sweeping(self):
        """Test simple parameter sweeping with --sweep arguments."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior:
        # --sweep.param1 val1 val2 --sweep.param2 val3 val4
        # should return list of configs with cartesian product

    def test_custom_parameter_sweeping(self):
        """Test custom parameter sweeping with --sweep_fn."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior:
        # --sweep_fn module.function should use custom generator
        # Generator should yield parameter override dictionaries

    def test_sweep_returns_list_of_configs(self):
        """Test that sweep mode returns list instead of single config."""
        pytest.skip("SymConfParser not implemented yet")

        # Expected behavior:
        # With --sweep: isinstance(result, list) should be True
        # Without --sweep: isinstance(result, list) should be False
