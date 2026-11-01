"""
Authentication & Cryptographic Sudo Module (Hexagonal Facade).
Preserves full backward compatibility while delegating to core.security and infrastructure.state.
"""

import time
import secrets
import threading
from typing import Optional, Dict, Any

from core.security import (
    hash_password, verify_password,
    generate_sudo_token as _sec_generate_sudo_token,
    verify_sudo_token as _sec_verify_sudo_token,
    _DEFAULT_HASH_123, PBKDF2_ITERATIONS
)
from infrastructure.state.sqlite_state import SQLiteStateProvider
import config

DB_FILE = getattr(config, "AUTH_DB_PATH", "db.json")
_db_lock = threading.Lock()
_sudo_lock = threading.Lock()
_sudo_tokens = {}

_state_instance = None
def _get_state():
    global _state_instance
    if _state_instance is None:
        _state_instance = SQLiteStateProvider()
    return _state_instance

DEFAULT_DB = {
    "setup_completed": False,
    "users": {
        "admin":   {"password_hash": _DEFAULT_HASH_123, "role": "admin",    "status": "active", "allowed_departments": ["hr", "finance", "it"]},
        "manager": {"password_hash": _DEFAULT_HASH_123, "role": "manager",  "status": "active", "allowed_departments": ["hr", "finance", "it"]},
        "hr1":     {"password_hash": _DEFAULT_HASH_123, "role": "employee", "status": "active", "allowed_departments": ["hr", "it"]},
        "hr2":     {"password_hash": _DEFAULT_HASH_123, "role": "employee", "status": "active", "allowed_departments": ["hr", "finance"]},
        "it1":     {"password_hash": _DEFAULT_HASH_123, "role": "employee", "status": "active", "allowed_departments": ["it"]},
        "it2":     {"password_hash": _DEFAULT_HASH_123, "role": "employee", "status": "active", "allowed_departments": ["it"]},
        "fin1":    {"password_hash": _DEFAULT_HASH_123, "role": "employee", "status": "active", "allowed_departments": ["finance"]},
        "fin2":    {"password_hash": _DEFAULT_HASH_123, "role": "employee", "status": "active", "allowed_departments": ["finance"]}
    },
    "departments": {
        "hr": {"status": "active"},
        "finance": {"status": "active"},
        "it": {"status": "active"}
    }
}

def generate_sudo_token(username: str, ip_address: str = "") -> str:
    """Issues short-lived elevated Sudo token, recording in persistent SQLite state."""
    state = _get_state()
    token = _sec_generate_sudo_token(username, client_ip=ip_address, state=state)
    with _sudo_lock:
        _sudo_tokens[token] = {
            "username": username,
            "ip_address": ip_address,
            "expires_at": time.time() + 300,
            "scope": "elevated_admin_action"
        }
    return token

def verify_sudo_token(token: str, username: str = None, ip_address: str = None) -> bool:
    with _sudo_lock:
        if token in _sudo_tokens:
            data = _sudo_tokens[token]
            if time.time() > data["expires_at"]:
                del _sudo_tokens[token]
                state = _get_state()
                state.delete_sudo_session(token)
                return False
            if username and data.get("username") != username:
                return False
            if ip_address and data.get("ip_address") and data.get("ip_address") != ip_address:
                return False
            return True

    state = _get_state()
    return _sec_verify_sudo_token(token, username=username, client_ip=ip_address, state=state)

def check_admin_sudo_barrier(username: str, sudo_token: str = None, ip_address: str = None, enforce: bool = False) -> tuple:
    if sudo_token:
        if not verify_sudo_token(sudo_token, username=username, ip_address=ip_address):
            return False, "Administrative Confirmation Required: Sudo token invalid or expired."
        return True, ""
    elif enforce:
        return False, "Administrative Confirmation Required: Sudo token required. Call /api/admin/verify-sudo."
    return True, ""

def load_db():
    state = _get_state()
    users = state.list_users()
    departments = state.list_departments()
    setup_done = state.get_setup_status()
    
    return {
        "setup_completed": setup_done,
        "users": {
            u.username: {
                "password_hash": u.password_hash,
                "role": u.role,
                "status": u.status,
                "allowed_departments": u.allowed_departments
            }
            for u in users
        },
        "departments": departments
    }

def save_db(data: dict):
    state = _get_state()
    from core.schemas import User
    if "setup_completed" in data:
        state.set_setup_completed(data["setup_completed"])
    if "departments" in data:
        for dname, dinfo in data["departments"].items():
            state.save_department(dname, status=dinfo.get("status", "active"))
    if "users" in data:
        for uname, uinfo in data["users"].items():
            u = User(
                username=uname,
                password_hash=uinfo.get("password_hash") or _DEFAULT_HASH_123,
                role=uinfo.get("role", "employee"),
                status=uinfo.get("status", "active"),
                allowed_departments=uinfo.get("allowed_departments", [])
            )
            state.save_user(u)
