"""
Hardware Probe Facade.
Re-exports probe utilities from platform_runtime.hardware_probe.
"""

from platform_runtime.hardware_probe import (
    probe_hardware,
    write_hardware_profile,
    detect_cpu_features,
    detect_memory,
    detect_gpu,
    detect_mps
)
