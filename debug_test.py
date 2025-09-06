"""Quick test to debug parser behavior."""

import tempfile
from pathlib import Path

import yaml

from twinconf import TwinConfParser

# Create temp config
with tempfile.TemporaryDirectory() as temp_dir:
    temp_dir = Path(temp_dir)

    config_data = {"server": {"host": "localhost", "port": 8080}, "debug": True}
    config_file = temp_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)

    parser = TwinConfParser()
    config = parser.parse_args([str(config_file)])

    print(f"Config type: {type(config)}")
    print(f"Config content: {config}")

    if hasattr(config, "server"):
        print(f"Server: {config.server}")
    else:
        print("No server attribute")
