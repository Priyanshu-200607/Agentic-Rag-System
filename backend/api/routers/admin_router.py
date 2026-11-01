"""
Administrative Operations Router (Hexagonal Ingress).
Guards user management and department lifecycle behind Sudo confirmation barriers.
"""

import re
import logging
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException, Depends

from core.schemas import User, UserCreate, AccessUpdate
from infrastructure.state.base import StateProvider
from api.dependencies import (
    get_state_provider, require_admin, require_admin_sudo, hash_password
)
from platform_runtime.audit_ledger import log_security_event

logger = logging.getLogger("rag_system")
router = APIRouter(tags=["Admin Operations"])

# --- USER MANAGEMENT ---

@router.get("/api/admin/users")
@router.get("/admin/users")
def get_users(admin_user = Depends(require_admin), state: StateProvider = Depends(get_state_provider)):
    users = state.list_users()
    return {
        u.username: {
            "role": u.role,
            "status": u.status,
            "allowed_departments": u.allowed_departments
        }
        for u in users
    }

@router.post("/api/admin/users")
@router.post("/admin/users")
def create_user(
    req: UserCreate,
    request: Request,
    admin_user = Depends(require_admin_sudo),
    state: StateProvider = Depends(get_state_provider)
):
    client_ip = request.client.host if request.client else "unknown"
    if not re.match(r"^[a-zA-Z0-9_-]{3,30}$", req.username):
        raise HTTPException(status_code=400, detail="Username must be 3-30 alphanumeric characters.")

    if state.get_user(req.username):
        raise HTTPException(status_code=400, detail="User already exists.")

    new_user = User(
        username=req.username,
        role=req.role,
        status="active",
        allowed_departments=req.allowed_departments,
        password_hash=hash_password(req.password)
    )
    state.save_user(new_user)
    log_security_event("USER_CREATED", admin_user.username, client_ip, "SUCCESS", {"created_user": req.username, "role": req.role})
    return {"success": True, "message": f"User {req.username} created."}

@router.delete("/api/admin/users/{username}")
@router.delete("/admin/users/{username}")
def delete_user(
    username: str,
    request: Request,
    admin_user = Depends(require_admin_sudo),
    state: StateProvider = Depends(get_state_provider)
):
    client_ip = request.client.host if request.client else "unknown"
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete master administrator account.")

    if not state.delete_user(username):
        raise HTTPException(status_code=404, detail="User not found.")

    log_security_event("USER_DELETED", admin_user.username, client_ip, "SUCCESS", {"deleted_user": username})
    return {"success": True, "message": f"User {username} deleted."}

@router.put("/api/admin/users/{username}/suspend")
@router.put("/admin/users/{username}/suspend")
def toggle_suspend_user(
    username: str,
    request: Request,
    admin_user = Depends(require_admin),
    state: StateProvider = Depends(get_state_provider)
):
    client_ip = request.client.host if request.client else "unknown"
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot suspend master administrator account.")

    user = state.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    new_status = "active" if user.status == "suspended" else "suspended"
    user.status = new_status
    state.save_user(user)

    log_security_event("USER_STATUS_TOGGLED", admin_user.username, client_ip, "SUCCESS", {"target_user": username, "new_status": new_status})
    return {"success": True, "new_status": new_status}

@router.put("/api/admin/users/{username}/access")
@router.put("/admin/users/{username}/access")
def update_user_access(
    username: str,
    req: AccessUpdate,
    request: Request,
    admin_user = Depends(require_admin),
    state: StateProvider = Depends(get_state_provider)
):
    client_ip = request.client.host if request.client else "unknown"
    user = state.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.allowed_departments = req.allowed_departments
    state.save_user(user)

    log_security_event("USER_ACCESS_UPDATED", admin_user.username, client_ip, "SUCCESS", {"target_user": username, "allowed_departments": req.allowed_departments})
    return {"success": True, "allowed_departments": req.allowed_departments}

# --- DEPARTMENT MANAGEMENT ---

@router.get("/api/admin/departments")
@router.get("/admin/departments")
def get_departments(admin_user = Depends(require_admin), state: StateProvider = Depends(get_state_provider)):
    return state.list_departments()

@router.post("/api/admin/departments/{name}")
@router.post("/admin/departments/{name}")
def create_department(
    name: str,
    request: Request,
    admin_user = Depends(require_admin),
    state: StateProvider = Depends(get_state_provider)
):
    client_ip = request.client.host if request.client else "unknown"
    if not re.match(r"^[a-zA-Z0-9_-]{2,60}$", name):
        raise HTTPException(status_code=400, detail="Invalid department name.")

    state.save_department(name, status="active")
    log_security_event("DEPARTMENT_CREATED", admin_user.username, client_ip, "SUCCESS", {"department": name})
    return {"success": True, "message": f"Department {name} created."}

@router.put("/api/admin/departments/{name}/suspend")
@router.put("/admin/departments/{name}/suspend")
def toggle_suspend_department(
    name: str,
    request: Request,
    admin_user = Depends(require_admin),
    state: StateProvider = Depends(get_state_provider)
):
    client_ip = request.client.host if request.client else "unknown"
    dept = state.get_department(name)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    new_status = "suspended" if dept.get("status") == "active" else "active"
    state.save_department(name, status=new_status)
    log_security_event("DEPARTMENT_SUSPENDED" if new_status == "suspended" else "DEPARTMENT_RESUMED", admin_user.username, client_ip, "SUCCESS", {"department": name})
    return {"success": True, "new_status": new_status}

@router.delete("/api/admin/departments/{name}")
@router.delete("/admin/departments/{name}")
def delete_department(
    name: str,
    request: Request,
    admin_user = Depends(require_admin_sudo),
    state: StateProvider = Depends(get_state_provider)
):
    client_ip = request.client.host if request.client else "unknown"
    state.delete_department(name)
    log_security_event("DEPARTMENT_DELETED", admin_user.username, client_ip, "SUCCESS", {"department": name})
    return {"success": True, "message": f"Department {name} deleted."}
