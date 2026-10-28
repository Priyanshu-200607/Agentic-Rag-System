import json
import os
import time
import secrets
import hashlib
import hmac
import threading
import config

DB_FILE = config.AUTH_DB_PATH

# Process-level lock for DB concurrency
_db_lock = threading.Lock()

# Thread-safe in-memory elevated sudo tokens: {token: {"username": str, "ip": str, "expires_at": float}}
_sudo_lock = threading.Lock()
_sudo_tokens = {}

# Standard PBKDF2-HMAC-SHA256 (600,000 iterations)
PBKDF2_ITERATIONS = 600000

def hash_password(plain_password: str, salt: bytes = None) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with 600,000 iterations and a unique 16-byte salt.
    Format: $pbkdf2-sha256$600000$<salt_hex>$<hash_hex>
    """
    if not plain_password:
        return ""
    if not salt:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"$pbkdf2-sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"

def verify_password(plain_password: str, stored_hash_or_plain: str) -> bool:
    """
    Timing-attack resistant verification of a plaintext password against a stored hash (or legacy plaintext).
    """
    if not plain_password or not stored_hash_or_plain:
        return False
        
    parts = stored_hash_or_plain.split("$")
    # Check for $pbkdf2-sha256$iterations$salt$hash format
    if len(parts) == 5 and parts[1] == "pbkdf2-sha256":
        try:
            iters = int(parts[2])
            salt = bytes.fromhex(parts[3])
            expected_dk = bytes.fromhex(parts[4])
            computed_dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iters)
            return hmac.compare_digest(computed_dk, expected_dk)
        except Exception:
            return False
            
    # Check for bcrypt if installed ($2b$, $2a$, $2y$)
    if stored_hash_or_plain.startswith("$2"):
        try:
            import bcrypt
            return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash_or_plain.encode("utf-8"))
        except ImportError:
            pass

    # Legacy plaintext constant-time comparison
    return hmac.compare_digest(plain_password.encode("utf-8"), stored_hash_or_plain.encode("utf-8"))

def generate_sudo_token(username: str, ip_address: str = "") -> str:
    """
    Issues a short-lived elevated Sudo Token (5-minute TTL) for critical administrative actions.
    """
    token = secrets.token_urlsafe(32)
    with _sudo_lock:
        _sudo_tokens[token] = {
            "username": username,
            "ip_address": ip_address,
            "expires_at": time.time() + 300, # 5 minutes
            "scope": "elevated_admin_action"
        }
    return token

def verify_sudo_token(token: str, username: str = None, ip_address: str = None) -> bool:
    """
    Validates that a sudo token exists, has not expired, and matches username and IP if provided.
    """
    if not token:
        return False
    with _sudo_lock:
        data = _sudo_tokens.get(token)
        if not data:
            return False
        if time.time() > data["expires_at"]:
            del _sudo_tokens[token]
            return False
        if username and data.get("username") != username:
            return False
        if ip_address and data.get("ip_address") and data.get("ip_address") != ip_address:
            return False
        return True

def check_admin_sudo_barrier(username: str, sudo_token: str = None, ip_address: str = None, enforce: bool = False) -> tuple:
    """
    Validates administrative sudo elevation barrier for destructive operations.
    Returns: (is_authorized: bool, error_message: str)
    """
    if sudo_token:
        if not verify_sudo_token(sudo_token, username=username, ip_address=ip_address):
            return False, "Administrative Confirmation Required: Sudo token invalid or expired."
        return True, ""
    elif enforce:
        return False, "Administrative Confirmation Required: Sudo token required. Call /api/admin/verify-sudo."
    return True, ""

# Pre-computed hash of initial default password "123" with fixed salt for bootstrapping
_DEFAULT_HASH_123 = "$pbkdf2-sha256$600000$1e07e2c1fd0f1db52c3209dd35d965fc$d20a780ca63b87b8a5ed55cf0c03d85ef4859fbb78a27a5f9746784527eebb6d"

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

def load_db():
    with _db_lock:
        if not os.path.exists(DB_FILE):
            _write_db_unsafe(DEFAULT_DB)
            return DEFAULT_DB
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Automatic transparent migration from plaintext to cryptographic hashes
        migrated = False
        if "users" in data:
            for username, user_info in data["users"].items():
                if "password" in user_info:
                    plain = user_info.pop("password")
                    user_info["password_hash"] = hash_password(plain)
                    migrated = True
                elif "password_hash" not in user_info:
                    user_info["password_hash"] = _DEFAULT_HASH_123
                    migrated = True
                    
        if "setup_completed" not in data:
            data["setup_completed"] = False
            migrated = True
            
        if migrated:
            _write_db_unsafe(data)
            
        return data

def save_db(data):
    with _db_lock:
        _write_db_unsafe(data)

def _write_db_unsafe(data):
    """Write db.json atomically using a temp file swap to prevent partial-write corruption."""
    import uuid
    tmp_path = f"{DB_FILE}.{uuid.uuid4().hex}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp_path, DB_FILE)
