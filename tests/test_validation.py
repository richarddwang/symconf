"""Test validation functionality as described in HOWTO.md."""

import tempfile

import pytest
import yaml

from symconf import SymConfParser
from symconf.exceptions import ParameterValidationError


class TestTypeValidation:
    """Test type validation functionality from HOWTO.md 驗證型別 section."""

    def test_type_validation_comprehensive_example(self):
        """Test the comprehensive type validation example from HOWTO.md."""
        # Create temporary config file matching HOWTO.md example
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.Child",
                "percent": 1,  # Error: should be float
                "animal": "pig",  # Error: should be 'cat' or 'dog'
                "dummy": False,  # Correct: no type annotation
                "toy": {"TYPE": "tests.test_objects.SuperToy"},  # Correct: object return value
                "stoy": {"TYPE": "tests.test_objects.Toy"},  # Error: Toy is not SuperToy subclass
                "number": {"TYPE": "tests.test_objects.square", "value": 0.3},  # Correct: function return
                "name": None,  # Correct: Optional in child class
                "vocab": ["a", "b"],  # Correct: container type first level only
                "stoy_cls": {"TYPE": "tests.test_objects.SuperToy"},  # Error: expects type not instance
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            # Import the classes for base_classes
            from tests.test_objects import Parent, SuperToy

            parser = SymConfParser(
                validate_type=True,
                base_classes={
                    "model": Parent,
                    "model.stoy": SuperToy,
                },
            )

            with pytest.raises(ParameterValidationError) as exc_info:
                parser.parse_args([config_path])

            error_str = str(exc_info.value)
            print("Actual error output:")
            print(error_str)

            # Check that all expected errors are present
            assert "Type mismatch" in error_str
            assert "model.percent" in error_str
            assert "Expected: float" in error_str
            assert "Actual: 1 (int)" in error_str

            assert "model.animal" in error_str
            assert "Literal['cat', 'dog']" in error_str
            assert "'pig' (str)" in error_str

            assert "model.stoy" in error_str
            assert "Expected: `SuperToy`" in error_str
            assert "Actual: `Toy`" in error_str

            assert "model.stoy_cls" in error_str
            assert "Type[`SuperToy`]" in error_str
            assert "`SuperToy`" in error_str

        finally:
            import os

            os.unlink(config_path)

    def test_type_validation_literal_types(self):
        """Test Literal type validation."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.Child",
                "percent": 0.5,
                "animal": "elephant",  # Invalid literal value
                "name": "test",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_type=True, validate_mapping=True)

            with pytest.raises(ParameterValidationError) as exc_info:
                parser.parse_args([config_path])

            error_str = str(exc_info.value)
            assert "Type mismatch" in error_str
            assert "model.animal" in error_str
            assert "Literal['cat', 'dog']" in error_str
            assert "'elephant' (str)" in error_str

        finally:
            import os

            os.unlink(config_path)

    def test_type_validation_union_types(self):
        """Test Union type validation."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.Parent",
                "name": "test",
                "number": "invalid",  # Should be int | float | None
                "vocab": [1.0, 2.0],  # Valid list[float]
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_type=True, validate_mapping=True)

            with pytest.raises(ParameterValidationError) as exc_info:
                parser.parse_args([config_path])

            error_str = str(exc_info.value)
            assert "Type mismatch" in error_str
            assert "model.number" in error_str

        finally:
            import os

            os.unlink(config_path)

    def test_type_validation_valid_types(self):
        """Test that valid types do not raise errors."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.Child",
                "percent": 0.8,  # Valid float
                "animal": "cat",  # Valid literal
                "name": "test",  # Valid string
                "toy": {"TYPE": "tests.test_objects.SuperToy"},  # Valid object
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_type=True, validate_mapping=True)

            # This should NOT raise an error
            parser.parse_args([config_path])

        finally:
            import os

            os.unlink(config_path)


class TestParameterMappingValidation:
    """Test parameter mapping validation from HOWTO.md 檢查不預期或缺失的參數 section."""

    def test_parameter_mapping_comprehensive_example(self):
        """Test the comprehensive parameter mapping example from HOWTO.md."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.ChildForMapping",
                # Missing required parameter 'a'
                # Missing required parameter 'd' (from parent)
                "c": 5,  # Error: object doesn't accept parameter 'c'
                "e": 7,  # Error: object doesn't accept parameter 'e'
            },
            "fn": {
                "TYPE": "tests.test_objects.func_for_mapping",
                "x": 3,
                "z": 5,  # Error: object doesn't accept parameter 'z'
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_mapping=True)

            with pytest.raises(ParameterValidationError) as exc_info:
                parser.parse_args([config_path])

            error_str = str(exc_info.value)
            print("Actual error output:")
            print(error_str)

            # Check for missing parameters
            assert "Missing parameters" in error_str
            assert "model.a" in error_str
            assert "model.d" in error_str
            assert "Object: ChildForMapping" in error_str

            # Check for unexpected parameters
            assert "Unexpected parameters" in error_str
            assert "model.c" in error_str
            assert "model.e" in error_str

            assert "fn.z" in error_str
            assert "Object: func_for_mapping" in error_str

        finally:
            import os

            os.unlink(config_path)

    def test_parameter_mapping_missing_required_params(self):
        """Test detection of missing required parameters."""
        config_data = {
            "fn": {
                "TYPE": "tests.test_objects.func_for_mapping",
                "x": 3,
                # Missing required parameter 'y'
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_mapping=True)

            with pytest.raises(ParameterValidationError) as exc_info:
                parser.parse_args([config_path])

            error_str = str(exc_info.value)
            assert "Missing parameters" in error_str
            assert "fn.y" in error_str
            assert "Object: func_for_mapping" in error_str

        finally:
            import os

            os.unlink(config_path)

    def test_parameter_mapping_unexpected_params(self):
        """Test detection of unexpected parameters (typos)."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.ChildForMapping",
                "a": 5,
                "d": 2.0,
                "typo_param": "value",  # Unexpected parameter
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_mapping=True)

            with pytest.raises(ParameterValidationError) as exc_info:
                parser.parse_args([config_path])

            error_str = str(exc_info.value)
            assert "Unexpected parameters" in error_str
            assert "model.typo_param" in error_str
            assert "Object: ChildForMapping" in error_str

        finally:
            import os

            os.unlink(config_path)

    def test_parameter_mapping_valid_params(self):
        """Test that valid parameter configurations do not raise errors."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.ChildForMapping",
                "a": 5,  # Required
                "d": 2.0,  # Required (from parent)
                "b": 10,  # Optional with default
            },
            "fn": {
                "TYPE": "tests.test_objects.func_for_mapping",
                "x": 3,
                "y": "test",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_mapping=True)

            # This should NOT raise an error
            parser.parse_args([config_path])

        finally:
            import os

            os.unlink(config_path)

    def test_parameter_mapping_with_kwargs(self):
        """Test parameter mapping with **kwargs parameter passing."""
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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_type=True, validate_mapping=True)

            # This should NOT raise an error since all parameters are valid
            # and traced through the **kwargs chain
            parser.parse_args([config_path])

        finally:
            import os

            os.unlink(config_path)


class TestValidationErrorMessageFormat:
    """Test that validation error messages match HOWTO.md format exactly."""

    def test_type_error_message_format(self):
        """Test type validation error message format."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.Child",
                "percent": 1,  # Type error: int instead of float
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_type=True, validate_mapping=True)

            with pytest.raises(ParameterValidationError) as exc_info:
                parser.parse_args([config_path])

            error_str = str(exc_info.value)

            # Check error message format matches HOWTO.md specification
            assert "❌ Type mismatch" in error_str
            assert "Parameter: model.percent" in error_str
            assert "Expected: float" in error_str
            assert "Actual: 1 (int)" in error_str

        finally:
            import os

            os.unlink(config_path)

    def test_literal_error_message_format(self):
        """Test Literal validation error message format."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.Child",
                "percent": 0.5,
                "animal": "pig",  # Literal error
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_type=True, validate_mapping=True)

            with pytest.raises(ParameterValidationError) as exc_info:
                parser.parse_args([config_path])

            error_str = str(exc_info.value)

            # Check error message format
            assert "❌ Type mismatch" in error_str
            assert "Parameter: model.animal" in error_str
            assert "Expected: Literal['cat', 'dog']" in error_str
            assert "Actual: 'pig' (str)" in error_str

        finally:
            import os

            os.unlink(config_path)

    def test_mapping_error_message_format(self):
        """Test parameter mapping error message format."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.ChildForMapping",
                "wrong_param": "value",  # Unexpected parameter
                # Missing required parameters
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_mapping=True)

            with pytest.raises(ParameterValidationError) as exc_info:
                parser.parse_args([config_path])

            error_str = str(exc_info.value)

            # Check error message format
            assert "❌ Missing parameters" in error_str
            assert "Parameters: model.a, model.d" in error_str
            assert "Object: ChildForMapping" in error_str

            assert "❌ Unexpected parameters" in error_str
            assert "Parameters: model.wrong_param" in error_str

        finally:
            import os

            os.unlink(config_path)


class TestValidationToggling:
    """Test enabling/disabling validation features."""

    def test_disable_type_validation(self):
        """Test that type validation can be disabled."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.Child",
                "percent": 1,  # Type error: int instead of float
                "animal": "pig",  # Literal error
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_type=False, validate_mapping=False)

            # This should NOT raise an error since validation is disabled
            parser.parse_args([config_path])

        finally:
            import os

            os.unlink(config_path)

    def test_disable_mapping_validation(self):
        """Test that mapping validation can be disabled."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.ChildForMapping",
                "wrong_param": "value",  # Unexpected parameter
                # Missing required parameters
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            parser = SymConfParser(validate_type=False, validate_mapping=False)

            # This should NOT raise an error since validation is disabled
            parser.parse_args([config_path])

        finally:
            import os

            os.unlink(config_path)

    def test_separate_validation_controls(self):
        """Test that type and mapping validation can be controlled separately."""
        config_data = {
            "model": {
                "TYPE": "tests.test_objects.Child",
                "percent": 1,  # Type error
                "animal": "cat",  # Valid literal
                "extra_param": "value",  # Mapping error
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            # Test type validation only (should catch type error but ignore mapping)
            parser_type_only = SymConfParser(validate_type=True, validate_mapping=False)

            with pytest.raises(ParameterValidationError) as exc_info:
                parser_type_only.parse_args([config_path])

            error_str = str(exc_info.value)
            assert "Type mismatch" in error_str
            assert "Unexpected parameters" not in error_str

            # Test mapping validation only (should catch mapping error but ignore type)
            parser_mapping_only = SymConfParser(validate_type=False, validate_mapping=True)

            with pytest.raises(ParameterValidationError) as exc_info:
                parser_mapping_only.parse_args([config_path])

            error_str = str(exc_info.value)
            assert "Unexpected parameters" in error_str
            assert "Type mismatch" not in error_str

        finally:
            import os

            os.unlink(config_path)
