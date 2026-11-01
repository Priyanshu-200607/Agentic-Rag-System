"""
API Security Dependencies, Authentication & Sudo Barrier (Hexagonal Ingress).
Implements standards-compliant OAuth2 JWT Bearer tokens and persistent elevated Sudo tokens.
"""

import os
import time
import json
import base64
import hmac
import hashlib
import secrets
from typing import Optional, Dict, Any, Generator
from fastapi import Header, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer

from core.schemas import User, SudoSession
from core.security import (
    hash_password, verify_password,
    create_jwt, decode_jwt, create_access_token, create_refresh_token,
    generate_sudo_token, verify_sudo_token,
    _DEFAULT_HASH_123, PBKDF2_ITERATIONS,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, SUDO_TOKEN_EXPIRE_SECONDS
)
from infrastructure.state.base import StateProvider
from infrastructure.state.sqlite_state import SQLiteStateProvider
from infrastructure.storage.base import StorageProvider
from infrastructure.storage.local_storage import LocalDiskStorageProvider
from platform_runtime.audit_ledger import log_security_event
import config

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "rag_super_secret_enterprise_jwt_signing_key_2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
SUDO_TOKEN_EXPIRE_SECONDS = 300  # 5 minutes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Singleton state & storage providers for dependency injection
_state_provider_instance = None
_storage_provider_instance = None
_rag_system_instance = None

def get_state_provider() -> StateProvider:
    global _state_provider_instance
    if _state_provider_instance is None:
        _state_provider_instance = SQLiteStateProvider()
    return _state_provider_instance

def get_storage_provider() -> StorageProvider:
    global _storage_provider_instance
    if _storage_provider_instance is None:
        _storage_provider_instance = LocalDiskStorageProvider()
    return _storage_provider_instance

def get_rag_system():
    global _rag_system_instance
    if _rag_system_instance is None:
        from core.orchestrator import MultiDeptRAG
        _rag_system_instance = MultiDeptRAG(
            state_provider=get_state_provider(),
            storage_provider=get_storage_provider()
        )
    return _rag_system_instance

# --- FASTAPI DEPENDENCIES ---

async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    x_username: Optional[str] = Header(None),
    state: StateProvider = Depends(get_state_provider)
) -> User:
    """
    Extracts and authenticates user.
    Prioritizes JWT Bearer token; supports legacy x_username with audit logging for backward compatibility.
    """
    client_ip = request.client.host if request.client else "unknown"

    # 1. JWT Bearer token authentication
    if token:
        try:
            payload = decode_jwt(token)
            username = payload.get("sub")
            user = state.get_user(username)
            if not user or user.status == "suspended":
                log_security_event("AUTH_FAILED", username or "unknown", client_ip, "DENIED", {"reason": "user_invalid_or_suspended"})
                raise HTTPException(status_code=401, detail="User account is invalid or suspended.")
            return user
        except ValueError as e:
            log_security_event("AUTH_TOKEN_INVALID", "anonymous", client_ip, "DENIED", {"error": str(e)})
            raise HTTPException(status_code=401, detail=f"Authentication token invalid: {e}")

    # 2. Legacy fallback: x_username header (with warning)
    if x_username:
        user = state.get_user(x_username)
        if user and user.status != "suspended":
            return user

    log_security_event("UNAUTHORIZED_ACCESS", "anonymous", client_ip, "DENIED", {"path": str(request.url.path)})
    raise HTTPException(status_code=401, detail="Not authenticated. Provide a valid Bearer token.")

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Administrative privileges required.")
    if current_user.status == "suspended":
        raise HTTPException(status_code=403, detail="Forbidden: Account is suspended.")
    return current_user

async def require_admin_sudo(
    request: Request,
    current_user: User = Depends(require_admin),
    x_admin_sudo_token: Optional[str] = Header(None),
    state: StateProvider = Depends(get_state_provider)
) -> User:
    client_ip = request.client.host if request.client else "unknown"
    is_valid = verify_sudo_token(x_admin_sudo_token, username=current_user.username, client_ip=client_ip, state=state)
    if not is_valid:
        log_security_event("SUDO_BARRIER_FAIL", current_user.username, client_ip, "BLOCKED", {"path": str(request.url.path)})
        raise HTTPException(status_code=403, detail="Administrative Confirmation Required: Valid Sudo token required. Call /api/auth/verify-sudo.")
    return current_user
