import json
import os
from hardware_probe import probe_hardware

def calculate_hardware_config():
    """
    Executes hardware profiling to compute dynamic batch sizes, thread tuning,
    device selection, and SQLite caching.
    Writes static hardware_config.json so runtime never has to re-poll GPU.
    """
    config = probe_hardware()
    config_path = os.path.join(os.path.dirname(__file__), "hardware_config.json")
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
        
    print(f"Hardware profiled and configuration written to {config_path}")
    print(json.dumps(config, indent=2))
    return config

if __name__ == "__main__":
    calculate_hardware_config()
