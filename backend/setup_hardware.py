import json
import os
import psutil

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

def calculate_hardware_config():
    config = {
        "device": "cpu",
        "kg_batch": 4,
        "chroma_batch": 500,
        "chunk_size": 500,
        "overlap": 100,
        "quantize_8bit": False,
        "total_ram_gb": psutil.virtual_memory().total / (1024**3),
        "vram_gb": 0
    }

    if HAS_TORCH:
        if torch.cuda.is_available():
            config["device"] = "cuda"
            try:
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                config["vram_gb"] = vram_gb
                
                if vram_gb >= 20:
                    config["kg_batch"] = 128
                    config["chroma_batch"] = 10000
                    config["chunk_size"] = 1000
                    config["overlap"] = 200
                elif vram_gb >= 12:
                    config["kg_batch"] = 32
                    config["chroma_batch"] = 5000
                    config["chunk_size"] = 750
                    config["overlap"] = 150
                    config["quantize_8bit"] = False # Not needed for 12GB+ usually
                else:
                    config["kg_batch"] = 16
                    config["chroma_batch"] = 2500
                    config["chunk_size"] = 600
                    config["overlap"] = 120
                    config["quantize_8bit"] = True
            except Exception as e:
                print(f"Error reading CUDA properties: {e}")
                
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            config["device"] = "mps"
            config["kg_batch"] = 8
            config["chroma_batch"] = 1000
            config["chunk_size"] = 500
            config["overlap"] = 100

    config_path = os.path.join(os.path.dirname(__file__), "hardware_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
        
    print(f"Hardware profiled and configuration written to {config_path}")
    print(json.dumps(config, indent=2))

if __name__ == "__main__":
    calculate_hardware_config()
