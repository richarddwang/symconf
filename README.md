# TwinConf
An entanglement of configuration and code.

## Construct configuration

**Given**: entrypoint python program instantiate TwinConf parser and fire its `parse_args`
```python: main.py
from twinconf import TwinConfParser

if __name__ == "__main__":
    parser = TwinConfParser()
    config = parser.parse_args()
```

### Sources
There are few ways to specify configuration value:

- YAML files: 
- Object's parameter default values
- Merge configuration in configuration library: 
- Command line interface arguments:

#### YAML file(s)

- **Given**: one or multiple configuration files
- **When**: `python main.py --config <yaml_file> --config <yaml_file>` 
- **Then**: the configuration values from the different YAML files should be loaded and nested merged (later yaml file has higher priority)

## Variable Interpolation



### Import environment variables

Given: one or multiple dotenv files 
And: `main.py` instantiate TwinConf parser and fire its `parse_args`
When: `python main.py --env <env_file> --env <env_file>`
Then: the environment variables defined in the dotenv files should be loaded and available in the application



