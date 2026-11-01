"""
Runtime Resource Manager.
Handles memory pressure monitoring, batch size scaling, hardware cache PRAGMAs,
and dynamic CPU/GPU device selection.
"""

import os
import gc
import json
import sys
import logging
from platform_runtime.thread_tuner import tune_threads

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger("rag_system")

class ResourceManager:
    _hardware_config = None

    @staticmethod
    def _load_config():
        if ResourceManager._hardware_config is None:
            config_path = os.path.join(os.path.dirname(__file__), "hardware_profile.json")
            legacy_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hardware_config.json")
            
            loaded = False
            for p in [config_path, legacy_config_path]:
                if os.path.exists(p):
                    try:
                        with open(p, "r") as f:
                            ResourceManager._hardware_config = json.load(f)
                            loaded = True
                            break
                    except Exception:
                        pass

            if not loaded:
                ResourceManager._hardware_config = {
                    "tier": "standard_consumer_cpu",
                    "device": "cpu",
                    "kg_batch": 4,
                    "chroma_batch": 1000,
                    "chunk_size": 500,
                    "overlap": 100,
                    "quantize_8bit": False,
                    "total_ram_gb": 8,
                    "vram_gb": 0,
                    "sqlite_cache_kb": 64000
                }
            ResourceManager.apply_thread_tuning()
        return ResourceManager._hardware_config

    @staticmethod
    def reload_config():
        ResourceManager._hardware_config = None
        return ResourceManager._load_config()

    @staticmethod
    def apply_thread_tuning():
        cfg = ResourceManager._load_config()
        cores = cfg.get("cpu", {}).get("cores") or os.cpu_count() or 4
        tune_threads(max(1, cores - 2))

    @staticmethod
    def get_tier():
        return ResourceManager._load_config().get("tier", "standard_consumer_cpu")

    @staticmethod
    def get_sqlite_cache_size():
        return ResourceManager._load_config().get("sqlite_cache_kb", 64000)

    @staticmethod
    def get_device():
        return ResourceManager._load_config().get("device", "cpu")

    @staticmethod
    def get_chunk_size():
        return ResourceManager._load_config().get("chunk_size", 500)

    @staticmethod
    def get_chunk_overlap():
        return ResourceManager._load_config().get("overlap", 100)

    @staticmethod
    def check_memory_pressure(threshold: float = 85.0) -> bool:
        """
        Monitors host RAM/VRAM utilization. Triggers garbage collection if over threshold.
        Returns True if memory pressure is critical.
        """
        if not HAS_PSUTIL:
            return False
            
        mem = psutil.virtual_memory()
        if mem.percent > threshold:
            logger.warning(f"[RESOURCE] High memory pressure detected: {mem.percent}%. Triggering GC collect.")
            gc.collect()
            if "torch" in sys.modules:
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass
            return True
        return False
