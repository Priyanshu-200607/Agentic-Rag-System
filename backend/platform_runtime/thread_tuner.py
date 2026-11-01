"""
Thread and NUMA affinity configuration for high-performance CPU inference.
"""

import os
import sys

def tune_threads(num_threads: int = None) -> int:
    """Sets OMP_NUM_THREADS, MKL_NUM_THREADS, and PyTorch threads based on physical core count."""
    threads = num_threads or max(1, (os.cpu_count() or 4) - 2)
    os.environ["OMP_NUM_THREADS"] = str(threads)
    os.environ["MKL_NUM_THREADS"] = str(threads)
    
    if "torch" in sys.modules:
        try:
            import torch
            torch.set_num_threads(threads)
        except Exception:
            pass
            
    return threads
