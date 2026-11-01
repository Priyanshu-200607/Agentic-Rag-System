"""
Platform Hardware Discovery and Tier Classification Probe.
Inspects CPU, RAM, CUDA, and Apple Silicon MPS capabilities without heavy imports.
"""

import os
import sys
import shutil
import subprocess
import platform
import json

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

def detect_cpu_features() -> dict:
    cpu_count = os.cpu_count() or 4
    features = {
        "cores": cpu_count,
        "arch": platform.machine(),
        "has_avx": False,
        "has_avx2": False,
        "has_avx512": False,
    }
    
    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r") as f:
                content = f.read().lower()
                features["has_avx"] = "avx" in content
                features["has_avx2"] = "avx2" in content
                features["has_avx512"] = "avx512" in content
        except Exception:
            pass
            
    return features

def detect_memory() -> dict:
    if HAS_PSUTIL:
        vm = psutil.virtual_memory()
        return {
            "total_ram_gb": round(vm.total / (1024**3), 2),
            "available_ram_gb": round(vm.available / (1024**3), 2),
        }
    return {"total_ram_gb": 8.0, "available_ram_gb": 4.0}

def detect_gpu() -> dict:
    gpu_info = {
        "has_cuda": False,
        "device_count": 0,
        "devices": [],
        "total_vram_gb": 0.0
    }
    
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            res = subprocess.run(
                [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = res.stdout.strip().split("\n")
                total_vram = 0.0
                devs = []
                for line in lines:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 2:
                        name = parts[0]
                        vram_mb = float(parts[1])
                        vram_gb = round(vram_mb / 1024.0, 2)
                        total_vram += vram_gb
                        devs.append({"name": name, "vram_gb": vram_gb})
                if devs:
                    gpu_info["has_cuda"] = True
                    gpu_info["device_count"] = len(devs)
                    gpu_info["devices"] = devs
                    gpu_info["total_vram_gb"] = round(total_vram, 2)
                    return gpu_info
        except Exception:
            pass
            
    if "torch" in sys.modules:
        try:
            import torch
            if torch.cuda.is_available():
                count = torch.cuda.device_count()
                devs = []
                total_vram = 0.0
                for i in range(count):
                    props = torch.cuda.get_device_properties(i)
                    vram_gb = round(props.total_memory / (1024**3), 2)
                    devs.append({"name": props.name, "vram_gb": vram_gb})
                    total_vram += vram_gb
                gpu_info["has_cuda"] = True
                gpu_info["device_count"] = count
                gpu_info["devices"] = devs
                gpu_info["total_vram_gb"] = round(total_vram, 2)
        except Exception:
            pass
            
    return gpu_info

def detect_mps() -> bool:
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return True
    return False

def probe_hardware() -> dict:
    cpu = detect_cpu_features()
    mem = detect_memory()
    gpu = detect_gpu()
    has_mps = detect_mps()
    
    total_ram = mem["total_ram_gb"]
    cores = cpu["cores"]
    has_gpu = gpu["has_cuda"]
    primary_vram = gpu["devices"][0]["vram_gb"] if has_gpu and gpu["devices"] else 0.0
    
    if has_mps:
        tier = "apple_silicon_mps"
        device = "mps"
        kg_batch = 10
        chroma_batch = 3000
        chunk_size = 750
        overlap = 150
        quantize_8bit = False
    elif has_gpu:
        if primary_vram >= 20.0:
            tier = "gpu_enterprise"
            device = "cuda"
            kg_batch = 128
            chroma_batch = 10000
            chunk_size = 1000
            overlap = 200
            quantize_8bit = False
        elif primary_vram >= 12.0:
            tier = "gpu_server"
            device = "cuda"
            kg_batch = 32
            chroma_batch = 5000
            chunk_size = 750
            overlap = 150
            quantize_8bit = False
        else:
            tier = "gpu_workstation"
            device = "cuda"
            kg_batch = 16
            chroma_batch = 2500
            chunk_size = 600
            overlap = 120
            quantize_8bit = True
    else:
        if cores >= 16 or total_ram >= 32.0:
            tier = "cpu_server"
            device = "cpu"
            kg_batch = 16
            chroma_batch = 4000
            chunk_size = 800
            overlap = 150
            quantize_8bit = False
        else:
            tier = "cpu_basic"
            device = "cpu"
            kg_batch = 4
            chroma_batch = 500
            chunk_size = 500
            overlap = 100
            quantize_8bit = False
            
    recommended_threads = max(1, cores - 2) if cores > 2 else 1
    sqlite_cache_kb = 2000000 if tier in ("cpu_server", "gpu_enterprise") else 64000
    
    return {
        "tier": tier,
        "device": device,
        "total_ram_gb": total_ram,
        "vram_gb": primary_vram,
        "cpu_cores": cores,
        "cpu_features": cpu,
        "gpu_info": gpu,
        "mps": has_mps,
        "thread_tuning": {
            "omp_num_threads": recommended_threads,
            "mkl_num_threads": recommended_threads,
            "torch_num_threads": recommended_threads
        },
        "sqlite_cache_kb": sqlite_cache_kb,
        "kg_batch": kg_batch,
        "chroma_batch": chroma_batch,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "quantize_8bit": quantize_8bit
    }

def write_hardware_profile(path: str = None) -> dict:
    profile = probe_hardware()
    target_path = path or os.path.join(os.path.dirname(__file__), "hardware_profile.json")
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=4)
    return profile
