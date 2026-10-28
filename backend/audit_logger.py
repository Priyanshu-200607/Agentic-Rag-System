import os
import json
import time
import threading
from datetime import datetime, timezone
import config

_audit_lock = threading.Lock()

def _get_audit_log_path() -> str:
    path_override = os.getenv("AUDIT_LOG_PATH")
    if path_override:
        return path_override
        
    candidate = os.path.join(config.BASE_DIR, "logs", "security_audit.jsonl")
    try:
        os.makedirs(os.path.dirname(candidate), exist_ok=True)
        # Test if directory is writable
        with open(candidate, "a", encoding="utf-8"):
            pass
        return candidate
    except (PermissionError, OSError):
        return os.path.join(config.BASE_DIR, "security_audit.jsonl")

AUDIT_LOG_FILE = _get_audit_log_path()

def log_security_event(event_type: str, actor: str, ip_address: str, status: str, details: dict = None):
    """
    Append-only structured JSONL audit logger for administrative actions and security events.
    Guarantees tamper-evident tracing for SOC2/ISO compliance.
    """
    global AUDIT_LOG_FILE
    target_path = _get_audit_log_path()
    AUDIT_LOG_FILE = target_path
    
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "epoch_time": time.time(),
        "event_type": event_type,
        "actor": actor,
        "ip_address": ip_address,
        "status": status,
        "details": details or {}
    }
    
    with _audit_lock:
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
