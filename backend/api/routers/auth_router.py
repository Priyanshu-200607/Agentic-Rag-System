"""
Authentication & Setup Router (Hexagonal Ingress).
Handles OAuth2 password login, JWT issuance, setup wizard, and Sudo elevation.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from core.schemas import Login, SetupRequest, SudoVerifyRequest, TokenResponse, SudoTokenResponse
from infrastructure.state.base import StateProvider
from api.dependencies import (
    get_state_provider, verify_password, hash_password,
    create_access_token, create_refresh_token, decode_jwt,
    generate_sudo_token
)
from platform_runtime.audit_ledger import log_security_event

router = APIRouter(tags=["Authentication"])

@router.post("/api/auth/login", response_model=TokenResponse)
@router.post("/login")
def login(req: Login, request: Request, state: StateProvider = Depends(get_state_provider)):
    client_ip = request.client.host if request.client else "unknown"
    user = state.get_user(req.username)
    
    if not user:
        log_security_event("LOGIN_FAIL", req.username, client_ip, "FAILED", {"reason": "user_not_found"})
        return {"success": False, "message": "User not found"}

    stored_hash = user.password_hash or ""
    if not verify_password(req.password, stored_hash):
        log_security_event("LOGIN_FAIL", req.username, client_ip, "FAILED", {"reason": "incorrect_password"})
        return {"success": False, "message": "Incorrect password"}

    if user.status == "suspended":
        log_security_event("LOGIN_BLOCKED", req.username, client_ip, "BLOCKED", {"reason": "account_suspended"})
        return {"success": False, "message": "Account suspended"}

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    setup_done = state.get_setup_status()
    
    log_security_event("LOGIN_SUCCESS", req.username, client_ip, "SUCCESS", {"role": user.role})

    # Returns both token format and legacy frontend format
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 900,
        "refresh_token": refresh_token,
        "username": user.username,
        "role": user.role,
        "allowed_departments": user.allowed_departments,
        "setup_completed": setup_done
    }

@router.post("/api/auth/refresh")
def refresh_token(request: Request, state: StateProvider = Depends(get_state_provider)):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Refresh token required in Authorization header.")
    
    raw_token = auth_header.split(" ")[1]
    try:
        payload = decode_jwt(raw_token)
        if payload.get("scope") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token scope. Refresh token required.")
        user = state.get_user(payload.get("sub"))
        if not user or user.status == "suspended":
            raise HTTPException(status_code=401, detail="User not found or suspended.")
        return {
            "access_token": create_access_token(user),
            "token_type": "bearer",
            "expires_in": 900
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token invalid or expired: {e}")

@router.get("/api/setup/status")
def get_setup_status(state: StateProvider = Depends(get_state_provider)):
    return {"setup_completed": state.get_setup_status()}

@router.post("/api/setup")
def setup_wizard(req: SetupRequest, request: Request, state: StateProvider = Depends(get_state_provider)):
    client_ip = request.client.host if request.client else "unknown"
    if state.get_setup_status():
        log_security_event("SETUP_WIZARD_LOCKED", "anonymous", client_ip, "BLOCKED", {"reason": "already_initialized"})
        raise HTTPException(status_code=403, detail="Forbidden: Initial setup has already been completed.")
        
    if len(req.admin_password) < 8:
        raise HTTPException(status_code=400, detail="Administrator password must be at least 8 characters long.")

    from core.schemas import User
    admin_user = state.get_user("admin")
    if not admin_user:
        admin_user = User(
            username="admin",
            role="admin",
            status="active",
            allowed_departments=["hr", "finance", "it"],
            password_hash=hash_password(req.admin_password)
        )
    else:
        admin_user.password_hash = hash_password(req.admin_password)
        
    state.save_user(admin_user)
    state.set_setup_completed(True)
    log_security_event("SETUP_WIZARD_COMPLETED", "admin", client_ip, "SUCCESS")
    return {"success": True, "message": "Administrator master credentials configured."}

@router.post("/api/auth/verify-sudo", response_model=SudoTokenResponse)
@router.post("/api/admin/verify-sudo")
def verify_admin_sudo(req: SudoVerifyRequest, request: Request, state: StateProvider = Depends(get_state_provider)):
    client_ip = request.client.host if request.client else "unknown"
    user = state.get_user(req.username)
    
    if not user or user.role != "admin":
        log_security_event("SUDO_AUTH_FAIL", req.username, client_ip, "DENIED", {"reason": "not_admin"})
        raise HTTPException(status_code=403, detail="Forbidden: Sudo verification requires an active administrator account.")

    if not verify_password(req.password, user.password_hash or ""):
        log_security_event("SUDO_AUTH_FAIL", req.username, client_ip, "FAILED", {"reason": "incorrect_password"})
        raise HTTPException(status_code=401, detail="Invalid administrator credentials.")

    token = generate_sudo_token(req.username, client_ip=client_ip, state=state)
    log_security_event("SUDO_AUTH_SUCCESS", req.username, client_ip, "SUCCESS", {"token_ttl": 300})
    return {
        "success": True,
        "sudo_token": token,
        "expires_in": 300,
        "message": "Sudo privileges granted for 5 minutes."
    }
