"""
Application Lifecycle & Signal Management.
Captures OS termination signals (SIGINT, SIGTERM, atexit) to commit SQLite WAL journals,
flush vector indexes, terminate background workers, and release GPU VRAM.
"""

import os
import sys
import signal
import atexit
import logging

logger = logging.getLogger("rag_app")

_cleanup_hooks = []

def register_cleanup_hook(hook):
    """Registers a callback function to be executed during graceful shutdown."""
    _cleanup_hooks.append(hook)

def execute_shutdown(signum=None, frame=None):
    logger.info(f"[LIFECYCLE] Received shutdown signal ({signum}). Initiating graceful termination...")
    for hook in _cleanup_hooks:
        try:
            hook()
        except Exception as e:
            logger.warning(f"[LIFECYCLE] Cleanup hook error: {e}")
    logger.info("[LIFECYCLE] Graceful shutdown complete. Exiting.")
    sys.exit(0)

def setup_signal_handlers():
    """Binds OS signals to graceful shutdown."""
    signal.signal(signal.SIGINT, execute_shutdown)
    signal.signal(signal.SIGTERM, execute_shutdown)
    atexit.register(execute_shutdown)
