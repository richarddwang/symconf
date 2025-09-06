"""Tests for basic configuration functionality."""

from twinconf import ConfigurationObject, TwinConfParser


class TestConfigurationObject:
    """Test the ConfigurationObject class."""

    def test_dict_style_access(self):
        """Test dictionary-style access."""
        config = ConfigurationObject({"key": "value", "nested": {"inner": 42}})

        assert config["key"] == "value"
        assert config["nested"]["inner"] == 42

    def test_attribute_style_access(self):
        """Test attribute-style access."""
        config = ConfigurationObject({"key": "value", "nested": {"inner": 42}})

        assert config.key == "value"
        assert config.nested.inner == 42

    def test_mixed_access_styles(self):
        """Test mixing dictionary and attribute access."""
        config = ConfigurationObject({"server": {"host": "localhost", "port": 8080}})

        assert config["server"].host == "localhost"
        assert config.server["port"] == 8080

    def test_setting_values(self):
        """Test setting values with both styles."""
        config = ConfigurationObject()

        # Dict style
        config["key1"] = "value1"
        assert config["key1"] == "value1"

        # Attribute style
        config.key2 = "value2"
        assert config.key2 == "value2"

    def test_nested_dict_conversion(self):
        """Test that nested dicts are converted to ConfigurationObject."""
        data = {"level1": {"level2": {"level3": "value"}}}
        config = ConfigurationObject(data)

        assert isinstance(config.level1, ConfigurationObject)
        assert isinstance(config.level1.level2, ConfigurationObject)
        assert config.level1.level2.level3 == "value"

    def test_get_method_with_default(self):
        """Test get method with default values."""
        config = ConfigurationObject({"existing": "value"})

        assert config.get("existing") == "value"
        assert config.get("missing", "default") == "default"
        assert config.get("missing") is None

    def test_pop_method(self):
        """Test pop method."""
        config = ConfigurationObject({"key": "value", "other": "data"})

        value = config.pop("key")
        assert value == "value"
        assert "key" not in config

        default_value = config.pop("missing", "default")
        assert default_value == "default"

    def test_kwargs_property(self):
        """Test kwargs property excludes special keys."""
        config = ConfigurationObject(
            {"TYPE": "some.Module", "CLASS": {"arg": "value"}, "MERGE": "some/file", "arg1": "value1", "arg2": 42}
        )

        kwargs = config.kwargs
        assert "TYPE" not in kwargs
        assert "CLASS" not in kwargs
        assert "MERGE" not in kwargs
        assert kwargs["arg1"] == "value1"
        assert kwargs["arg2"] == 42

    def test_pretty_method(self):
        """Test pretty method for flattened representation."""
        config = ConfigurationObject(
            {"server": {"host": "localhost", "port": 8080}, "database": {"url": "sqlite:///:memory:"}}
        )

        pretty = config.pretty()
        expected = {"server.host": "localhost", "server.port": 8080, "database.url": "sqlite:///:memory:"}
        assert pretty == expected

    def test_pretty_method_with_exclusions(self):
        """Test pretty method with exclusions."""
        config = ConfigurationObject({"server": {"host": "localhost", "port": 8080}, "secret": "password"})

        pretty = config.pretty(exclude=["secret"])
        assert "server.host" in pretty
        assert "server.port" in pretty
        assert "secret" not in pretty


class TestTwinConfParser:
    """Test the TwinConfParser class."""

    def test_parser_initialization(self):
        """Test parser initialization with default settings."""
        parser = TwinConfParser()
        assert parser.validate_types is True
        assert parser.check_missing_args is True
        assert parser.check_unexpected_args is True
        assert parser.base_classes == {}

    def test_parser_with_custom_settings(self):
        """Test parser with custom validation settings."""
        base_classes = {"model": object}
        parser = TwinConfParser(
            base_classes=base_classes, validate_types=False, check_missing_args=False, check_unexpected_args=False
        )

        assert parser.validate_types is False
        assert parser.check_missing_args is False
        assert parser.check_unexpected_args is False
        assert parser.base_classes == base_classes
