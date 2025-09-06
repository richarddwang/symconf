"""Tests for YAML file parsing and merging functionality."""

import os

import yaml

from twinconf import TwinConfParser


class TestYAMLParsing:
    """Test YAML file parsing functionality."""

    def test_single_yaml_file(self, temp_dir):
        """Test parsing a single YAML file."""
        # Create test YAML file
        config_data = {"server": {"host": "localhost", "port": 8080}, "debug": True}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file)])

        assert config.server.host == "localhost"
        assert config.server.port == 8080
        assert config.debug is True

    def test_multiple_yaml_files_merge(self, temp_dir):
        """Test merging multiple YAML files."""
        # Create first config file
        config1_data = {"server": {"host": "localhost", "ports": [8080, 8081]}}
        config1_file = temp_dir / "config1.yaml"
        with open(config1_file, "w") as f:
            yaml.safe_dump(config1_data, f)

        # Create second config file
        config2_data = {
            "server": {
                "timeout": 10,
                "ports": [9090],  # This should replace the first ports list
            }
        }
        config2_file = temp_dir / "config2.yaml"
        with open(config2_file, "w") as f:
            yaml.safe_dump(config2_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config1_file), str(config2_file)])

        assert config.server.host == "localhost"
        assert config.server.timeout == 10
        assert config.server.ports == [9090]  # Later file should override

    def test_dotenv_file_loading(self, temp_dir):
        """Test loading dotenv files."""
        # Create dotenv file
        env_file = temp_dir / ".env"
        with open(env_file, "w") as f:
            f.write("DATABASE_URL=postgresql://localhost/test\n")
            f.write("DEBUG=true\n")
            f.write("PORT=9000\n")

        # Create YAML file that references environment variables
        config_data = {"database": {"url": "${DATABASE_URL}"}, "debug": "${DEBUG}", "port": "${PORT}"}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file), "--env", str(env_file)])

        assert config.database.url == "postgresql://localhost/test"
        assert config.debug is True  # YAML parsing converts "true" to boolean
        assert config.port == 9000  # Should be parsed as int

    def test_merge_keyword_functionality(self, temp_dir):
        """Test MERGE keyword functionality."""
        # Create base config file
        base_config = {"server": {"timeout": 10, "port": 9090}}
        base_file = temp_dir / "base.yaml"
        with open(base_file, "w") as f:
            yaml.safe_dump(base_config, f)

        # Create nested config file
        nested_config = {"more_level": {"server2": {"port": 7070, "host": "awesome.com"}}}
        nested_file = temp_dir / "nested.yaml"
        with open(nested_file, "w") as f:
            yaml.safe_dump(nested_config, f)

        # Create main config file with MERGE
        main_config = {
            "MERGE": "base",
            "server": {"host": "localhost", "MERGE": "nested.more_level.server2", "port": 8080},
        }
        main_file = temp_dir / "config.yaml"
        with open(main_file, "w") as f:
            yaml.safe_dump(main_config, f)

        # Change to temp directory for relative path resolution
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            parser = TwinConfParser()
            config = parser.parse_args([str(main_file)])

            # Should have merged values
            assert config.server.timeout == 10  # From base
            assert config.server.host == "localhost"  # From main (overrides nested)
            assert config.server.port == 8080  # From main (final override)
        finally:
            os.chdir(old_cwd)

    def test_remove_keyword_functionality(self, temp_dir):
        """Test REMOVE keyword functionality."""
        # Create base config
        base_config = {"server": {"timeout": 10, "port": 9090}}
        base_file = temp_dir / "base.yaml"
        with open(base_file, "w") as f:
            yaml.safe_dump(base_config, f)

        # Create main config with REMOVE
        main_config = {"server": {"MERGE": "base.server", "timeout": "REMOVE"}}
        main_file = temp_dir / "config.yaml"
        with open(main_file, "w") as f:
            yaml.safe_dump(main_config, f)

        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            parser = TwinConfParser()
            config = parser.parse_args([str(main_file)])

            # Should have port but not timeout
            assert config.server.port == 9090
            assert "timeout" not in config.server
        finally:
            os.chdir(old_cwd)


class TestCommandLineOverrides:
    """Test command line argument override functionality."""

    def test_simple_cli_override(self, temp_dir):
        """Test simple command line overrides."""
        config_data = {"exp": {"seed": 42}, "model": {"learning_rate": 0.01}}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args([str(config_file), "--args", "exp.seed=3", "exp.name=hi", "model.learning_rate=0.1"])

        assert config.exp.seed == 3
        assert config.exp.name == "hi"
        assert config.model.learning_rate == 0.1

    def test_complex_value_parsing(self, temp_dir):
        """Test parsing complex values from command line."""
        config_data = {"placeholder": "value"}
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        parser = TwinConfParser()
        config = parser.parse_args(
            [
                str(config_file),
                "--args",
                "int_val=42",
                "float_val=3.14",
                "bool_val=true",
                "list_val=[1,2,3]",
                'str_val="hello world"',
            ]
        )

        assert config.int_val == 42
        assert config.float_val == 3.14
        assert config.bool_val is True
        assert config.list_val == [1, 2, 3]
        assert config.str_val == "hello world"
