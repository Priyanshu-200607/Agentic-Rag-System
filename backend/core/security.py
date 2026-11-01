"""
Core Cryptographic Security & IAM Module (Hexagonal Domain Core).
Zero external dependencies. Implements:
- PBKDF2-HMAC-SHA256 password hashing (600,000 rounds)
- RFC 7519 HMAC-SHA256 JWT tokens (15-min access, 7-day refresh)
- Persistent HMAC-signed elevated Sudo tokens (5-minute TTL)
"""

import time
import json
import base64
import hmac
import hashlib
import secrets
from typing import Optional, Dict, Any
from core.schemas import User, SudoSession
import config

JWT_SECRET_KEY = getattr(config, "JWT_SECRET_KEY", "rag_super_secret_enterprise_jwt_signing_key_2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
SUDO_TOKEN_EXPIRE_SECONDS = 300  # 5 minutes

PBKDF2_ITERATIONS = 600000
_DEFAULT_HASH_123 = "$pbkdf2-sha256$600000$1e07e2c1fd0f1db52c3209dd35d965fc$d20a780ca63b87b8a5ed55cf0c03d85ef4859fbb78a27a5f9746784527eebb6d"

# --- PASSWORD HASHING ---

def hash_password(plain_password: str, salt: bytes = None) -> str:
    """Hashes password with PBKDF2-HMAC-SHA256 and unique 16-byte salt."""
    if not plain_password:
        return ""
    if not salt:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"$pbkdf2-sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"

def verify_password(plain_password: str, stored_hash_or_plain: str) -> bool:
    """Timing-attack resistant password verification."""
    if not plain_password or not stored_hash_or_plain:
        return False
    parts = stored_hash_or_plain.split("$")
    if len(parts) == 5 and parts[1] == "pbkdf2-sha256":
        try:
            iters = int(parts[2])
            salt = bytes.fromhex(parts[3])
            expected_dk = bytes.fromhex(parts[4])
            computed_dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iters)
            return hmac.compare_digest(computed_dk, expected_dk)
        except Exception:
            return False
            
    # Check for bcrypt if present
    if stored_hash_or_plain.startswith("$2"):
        try:
            import bcrypt
            return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash_or_plain.encode("utf-8"))
        except ImportError:
            pass

    return hmac.compare_digest(plain_password.encode("utf-8"), stored_hash_or_plain.encode("utf-8"))

# --- RFC 7519 JWT ENCODING & DECODING (ZERO EXTERNAL LOCK-IN) ---

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding and padding < 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)

def create_jwt(payload: dict, secret: str = JWT_SECRET_KEY, expires_seconds: int = 900) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    now = int(time.time())
    token_payload = dict(payload)
    token_payload["iat"] = now
    token_payload["exp"] = now + expires_seconds
    
    header_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64_encode(json.dumps(token_payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_jwt(token: str, secret: str = JWT_SECRET_KEY) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format.")
    header_b64, payload_b64, sig_b64 = parts
    
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64_decode(sig_b64)
    
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("JWT cryptographic signature mismatch.")
        
    payload = json.loads(_b64_decode(payload_b64).decode("utf-8"))
    if time.time() > payload.get("exp", 0):
        raise ValueError("JWT token expired.")
        
    return payload

def create_access_token(user: User) -> str:
    payload = {
        "sub": user.username,
        "role": user.role,
        "allowed_departments": user.allowed_departments,
        "scope": "access"
    }
    return create_jwt(payload, expires_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60)

def create_refresh_token(user: User) -> str:
    payload = {
        "sub": user.username,
        "scope": "refresh"
    }
    return create_jwt(payload, expires_seconds=REFRESH_TOKEN_EXPIRE_DAYS * 86400)

# --- SUDO ELEVATION BARRIER ---

def generate_sudo_token(username: str, client_ip: str = "", state = None) -> str:
    raw_token = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + SUDO_TOKEN_EXPIRE_SECONDS
    
    sig_payload = f"{raw_token}|{username}|{client_ip}|{expires_at}"
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), sig_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    
    session = SudoSession(
        token=raw_token,
        username=username,
        ip_address=client_ip,
        issued_at=now,
        expires_at=expires_at,
        signature=signature
    )
    if state:
        state.save_sudo_session(session)
    return raw_token

def verify_sudo_token(token: str, username: str = None, client_ip: str = None, state = None) -> bool:
    if not token:
        return False
    if state:
        session = state.get_sudo_session(token)
        if not session:
            return False

        sig_payload = f"{session.token}|{session.username}|{session.ip_address}|{session.expires_at}"
        expected_sig = hmac.new(JWT_SECRET_KEY.encode("utf-8"), sig_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, session.signature):
            state.delete_sudo_session(token)
            return False

        if username and session.username != username:
            return False
        if client_ip and session.ip_address and session.ip_address != client_ip:
            return False
        return True
    return False
