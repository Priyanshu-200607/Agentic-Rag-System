import os
import gc
import config

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

class ResourceManager:
    @staticmethod
    def get_device():
        if not HAS_TORCH:
            return "cpu"
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    @staticmethod
    def get_optimal_batch_sizes():
        device = ResourceManager.get_device()
        
        # Default fallback
        kg_batch = 8
        chroma_batch = 1000

        if device == "cuda":
            # Rough VRAM heuristic
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            if vram_gb >= 20: # e.g. A100, RTX 3090, 4090
                kg_batch = 128
                chroma_batch = 10000
            elif vram_gb >= 12: # e.g. RTX 4070
                kg_batch = 32
                chroma_batch = 5000
            else: # e.g. RTX 4060 8GB
                kg_batch = 16
                chroma_batch = 2500
        elif device == "mps": # MacBook
            kg_batch = 8
            chroma_batch = 1000
        else: # CPU
            kg_batch = 4
            chroma_batch = 500
            
        return {"kg_batch": kg_batch, "chroma_batch": chroma_batch}

    @staticmethod
    def should_quantize_8bit():
        device = ResourceManager.get_device()
        if device != "cuda":
            return False
            
        # Check if bitsandbytes is available
        try:
            import bitsandbytes
            HAS_BNB = True
        except ImportError:
            HAS_BNB = False
            
        if not HAS_BNB:
            return False
            
        # Check VRAM limit
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return vram_gb < 12  # Quantize if less than 12GB VRAM to prevent OOM

    @staticmethod
    def check_memory_pressure(current_batch_size, min_batch_size=2):
        """Active backpressure: check system RAM and VRAM, throttle if needed."""
        pressure_detected = False
        
        # 1. Check System RAM
        if HAS_PSUTIL:
            ram_percent = psutil.virtual_memory().percent
            if ram_percent > 90:
                print(f"[Resource Manager] CRITICAL: System RAM at {ram_percent}%. Engaging backpressure.")
                pressure_detected = True

        # 2. Check GPU VRAM
        device = ResourceManager.get_device()
        if device == "cuda" and HAS_TORCH:
            try:
                # reserved memory vs total memory
                total = torch.cuda.get_device_properties(0).total_memory
                reserved = torch.cuda.memory_reserved(0)
                vram_percent = (reserved / total) * 100
                if vram_percent > 90:
                    print(f"[Resource Manager] CRITICAL: GPU VRAM at {vram_percent:.1f}%. Engaging backpressure.")
                    pressure_detected = True
            except Exception:
                pass
                
        if pressure_detected:
            # Trigger garbage collection and cache clearing
            gc.collect()
            if device == "cuda" and HAS_TORCH:
                torch.cuda.empty_cache()
                
            # Throttle batch size
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
            # Llama 3/3.1 supports massive context
            return 128000
        elif "mistral" in name or "mixtral" in name:
            return 32000
        
        # Fallback to config default
        return config.MAX_CONTEXT_CHARS
