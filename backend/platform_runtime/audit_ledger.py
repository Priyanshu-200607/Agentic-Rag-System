"""
Cryptographic Tamper-Evident Security Audit Ledger.
Links audit entries into an append-only SHA-256 hash chain resistant to local log tampering.
"""

import os
import json
import time
import hashlib
import threading
from typing import Dict, Any, Optional

_audit_lock = threading.Lock()

def _get_audit_log_path() -> str:
    path_override = os.getenv("AUDIT_LOG_PATH")
    if path_override:
        return path_override
        
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(base_dir, "logs", "security_audit.jsonl")
    try:
        os.makedirs(os.path.dirname(candidate), exist_ok=True)
        # Test if directory is writable
        with open(candidate, "a", encoding="utf-8"):
            pass
        return candidate
    except (PermissionError, OSError):
        return os.path.join(base_dir, "security_audit.jsonl")

AUDIT_LOG_FILE = _get_audit_log_path()

class AuditLedger:
    """Tamper-evident append-only ledger with cryptographic SHA-256 hash chaining."""

    def __init__(self, log_path: str = None):
        self.log_path = log_path or _get_audit_log_path()
        self._last_hash = self._compute_last_hash()

    def _compute_last_hash(self) -> str:
        if not os.path.exists(self.log_path):
            return "0" * 64
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    return "0" * 64
                last_line = lines[-1].strip()
                if last_line:
                    record = json.loads(last_line)
                    return record.get("record_hash", "0" * 64)
        except Exception:
            pass
        return "0" * 64

    def log_event(
        self,
        event_type: str,
        actor: str = "anonymous",
        ip_address: str = "unknown",
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        username: str = None,
        client_ip: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        global AUDIT_LOG_FILE
        target_path = _get_audit_log_path()
        self.log_path = target_path
        AUDIT_LOG_FILE = target_path

        effective_actor = username or actor
        effective_ip = client_ip or ip_address

        with _audit_lock:
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            details_clean = details or {}
            details_serialized = json.dumps(details_clean, sort_keys=True)
            
            raw_payload = f"{self._last_hash}|{timestamp}|{event_type}|{effective_actor}|{effective_ip}|{status}|{details_serialized}"
            record_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

            entry = {
                "timestamp": timestamp,
                "epoch_time": time.time(),
                "event_type": event_type,
                "actor": effective_actor,
                "username": effective_actor,
                "ip_address": effective_ip,
                "status": status,
                "details": details_clean,
                "prev_hash": self._last_hash,
                "record_hash": record_hash
            }

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

            self._last_hash = record_hash
            return entry

    def verify_integrity(self) -> tuple:
        if not os.path.exists(self.log_path):
            return True, 0, "No audit log file present."

        with _audit_lock:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            expected_prev = "0" * 64
            for idx, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    prev_hash = record.get("prev_hash")
                    recorded_hash = record.get("record_hash")
                    
                    if prev_hash != expected_prev:
                        return False, idx + 1, f"Hash chain broken at line {idx + 1}: prev_hash mismatch."

                    details_serialized = json.dumps(record.get("details", {}), sort_keys=True)
                    raw_payload = f"{prev_hash}|{record.get('timestamp')}|{record.get('event_type')}|{record.get('actor', record.get('username'))}|{record.get('ip_address')}|{record.get('status')}|{details_serialized}"
                    computed_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

                    if computed_hash != recorded_hash:
                        return False, idx + 1, f"Cryptographic tamper detected at line {idx + 1}: record_hash mismatch."

                    expected_prev = recorded_hash
                except Exception as e:
                    return False, idx + 1, f"Parse error at line {idx + 1}: {e}"

            return True, len(lines), "Audit ledger integrity verified."

_global_ledger = None

def get_audit_ledger() -> AuditLedger:
    global _global_ledger
    if _global_ledger is None:
        _global_ledger = AuditLedger()
    return _global_ledger

def log_security_event(
    event_type: str,
    actor: str = "anonymous",
    ip_address: str = "unknown",
    status: str = "SUCCESS",
    details: dict = None,
    username: str = None,
    client_ip: str = None,
    **kwargs
):
    effective_ip = client_ip or ip_address
    effective_actor = username or actor
    return get_audit_ledger().log_event(
        event_type,
        actor=effective_actor,
        ip_address=effective_ip,
        status=status,
        details=details,
        **kwargs
    )
