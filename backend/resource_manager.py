import os
import gc
import json
import sys
import config

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

class ResourceManager:
    _hardware_config = None

    @staticmethod
    def _load_config():
        if ResourceManager._hardware_config is None:
            config_path = os.path.join(os.path.dirname(__file__), "hardware_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    ResourceManager._hardware_config = json.load(f)
            else:
                # Safe fallback if boot script didn't run
                ResourceManager._hardware_config = {
                    "tier": "cpu_basic",
                    "device": "cpu",
                    "kg_batch": 4,
                    "chroma_batch": 500,
                    "chunk_size": 500,
                    "overlap": 100,
                    "quantize_8bit": False,
                    "total_ram_gb": 8,
                    "vram_gb": 0,
                    "sqlite_cache_kb": 64000,
                    "thread_tuning": {
                        "omp_num_threads": 4,
                        "mkl_num_threads": 4,
                        "torch_num_threads": 4
                    }
                }
            # Apply CPU thread optimizations at boot
            ResourceManager.apply_thread_tuning()
        return ResourceManager._hardware_config

    @staticmethod
    def reload_config():
        """Clears cached config and forces a reload (used after hardware re-sync)."""
        ResourceManager._hardware_config = None
        return ResourceManager._load_config()

    @staticmethod
    def apply_thread_tuning():
        """Optimizes OpenMP, MKL, and PyTorch threads based on hardware profile."""
        if not ResourceManager._hardware_config:
            return
        tt = ResourceManager._hardware_config.get("thread_tuning", {})
        omp = str(tt.get("omp_num_threads", 4))
        mkl = str(tt.get("mkl_num_threads", 4))
        torch_t = tt.get("torch_num_threads", 4)
        
        os.environ["OMP_NUM_THREADS"] = omp
        os.environ["MKL_NUM_THREADS"] = mkl
        
        if "torch" in sys.modules:
            try:
                import torch
                torch.set_num_threads(torch_t)
            except Exception:
                pass

    @staticmethod
    def get_tier():
        return ResourceManager._load_config().get("tier", "cpu_basic")

    @staticmethod
    def get_sqlite_cache_size():
        """Returns optimal PRAGMA cache_size in KB (e.g. 2,000,000 KB for 2GB cache on RAM servers)."""
        return ResourceManager._load_config().get("sqlite_cache_kb", 64000)

    @staticmethod
    def get_device():
        return ResourceManager._load_config().get("device", "cpu")

    @staticmethod
    def get_optimal_batch_sizes():
        cfg = ResourceManager._load_config()
        return {
            "kg_batch": cfg.get("kg_batch", 8),
            "chroma_batch": cfg.get("chroma_batch", 1000)
        }

    @staticmethod
    def get_optimal_chunk_sizes():
        cfg = ResourceManager._load_config()
        return {
            "chunk_size": cfg.get("chunk_size", 500),
            "overlap": cfg.get("overlap", 100)
        }

    @staticmethod
    def should_quantize_8bit():
        return ResourceManager._load_config().get("quantize_8bit", False)

    @staticmethod
    def check_memory_pressure(current_batch_size, min_batch_size=2):
        """Active backpressure: check system RAM and VRAM, throttle if needed."""
        
        # On-premise deployment: trust the boot configuration fully
        if os.getenv("DEPLOYMENT_TYPE", "cloud") == "on_premise":
            return current_batch_size

        pressure_detected = False
        
        # 1. Check System RAM
        if HAS_PSUTIL:
            ram_percent = psutil.virtual_memory().percent
            if ram_percent > 90:
                print(f"[Resource Manager] CRITICAL: System RAM at {ram_percent}%. Engaging backpressure.")
                pressure_detected = True

        # 2. Check GPU VRAM
        device = ResourceManager.get_device()
        if device == "cuda":
            try:
                import torch
                total = torch.cuda.get_device_properties(0).total_memory
                reserved = torch.cuda.memory_reserved(0)
                vram_percent = (reserved / total) * 100
                if vram_percent > 90:
                    print(f"[Resource Manager] CRITICAL: GPU VRAM at {vram_percent:.1f}%. Engaging backpressure.")
                    pressure_detected = True
            except Exception:
                pass
                
        if pressure_detected:
            gc.collect()
            if device == "cuda":
                try:
                    import torch
                    torch.cuda.empty_cache()
                except Exception:
                    pass
                
            new_batch = max(min_batch_size, current_batch_size // 2)
            if new_batch < current_batch_size:
                print(f"[Resource Manager] Throttling batch size from {current_batch_size} to {new_batch}.")
            return new_batch
            
        return current_batch_size

    @staticmethod
    def get_dynamic_context_limit(llm_model_name):
        """Dynamically set the context window limit based on the model."""
        name = llm_model_name.lower()
        if "gemma2" in name or "llama2" in name:
            return 8000
        elif "llama3" in name:
            return 128000
        elif "mistral" in name or "mixtral" in name:
            return 32000
        return config.MAX_CONTEXT_CHARS
