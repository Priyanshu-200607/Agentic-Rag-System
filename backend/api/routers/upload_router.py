"""
Upload & Document Ingestion Router (Hexagonal Ingress).
Handles multi-modal document ingestion, history queries, and document deletion.
"""

import os
import re
import logging
from typing import List, Optional
from fastapi import APIRouter, Form, File, UploadFile, Header, Request, HTTPException, Depends

from infrastructure.state.base import StateProvider
from infrastructure.storage.base import StorageProvider
from api.dependencies import get_state_provider, get_storage_provider, get_rag_system, require_admin, require_admin_sudo
from platform_runtime.audit_ledger import log_security_event

logger = logging.getLogger("rag_system")
router = APIRouter(tags=["Upload & Documents"])

@router.post("/api/upload")
@router.post("/upload")
async def upload_documents(
    department: str = Form(...),
    files: List[UploadFile] = File(...),
    x_username: Optional[str] = Header(None),
    state: StateProvider = Depends(get_state_provider),
    storage: StorageProvider = Depends(get_storage_provider),
    system = Depends(get_rag_system)
):
    if not x_username:
        raise HTTPException(status_code=401, detail="Unauthorized: User header required.")
    user = state.get_user(x_username)
    if not user or user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Forbidden: Only admins and managers can upload.")
    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="Forbidden: Account is suspended.")

    if not re.match(r"^[a-zA-Z0-9_-]{2,60}$", department):
        raise HTTPException(status_code=400, detail="Invalid department name. Must be 2-60 alphanumeric characters.")

    # Ensure department exists in state
    if not state.get_department(department):
        state.save_department(department, status="active")

    saved_paths = []
    for file in files:
        safe_filename = os.path.basename(file.filename)
        content = await file.read()
        saved_path = storage.save_file(department, safe_filename, content)
        saved_paths.append(saved_path)

    try:
        system.admin_upload_to_department(department, saved_paths)
    except Exception as e:
        logger.error(f"[SYSTEM] Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success", "files_uploaded": len(saved_paths)}

@router.get("/api/history")
@router.get("/history")
def get_history(
    username: str,
    state: StateProvider = Depends(get_state_provider),
    storage: StorageProvider = Depends(get_storage_provider)
):
    user = state.get_user(username)
    if not user:
        return {"history": [], "allowed": []}

    is_admin = user.role == "admin"
    all_depts = state.list_departments()
    allowed = list(all_depts.keys()) if is_admin else [d for d in user.allowed_departments if d in all_depts]

    history = []
    for dept in allowed:
        dept_files = storage.list_files(dept)
        for f in dept_files:
            history.append({"filename": f, "department": dept})

    return {
        "history": history,
        "allowed": allowed
    }

@router.delete("/api/upload/{department}/{filename}")
@router.delete("/upload/{department}/{filename}")
def delete_file(
    department: str,
    filename: str,
    request: Request,
    x_username: Optional[str] = Header(None),
    admin_user = Depends(require_admin),
    storage: StorageProvider = Depends(get_storage_provider),
    system = Depends(get_rag_system)
):
    client_ip = request.client.host if request.client else "unknown"
    safe_filename = os.path.basename(filename)
    file_path = storage.get_file_path(department, safe_filename)
    
    system.admin_delete_file(department, file_path)
    storage.delete_file(department, safe_filename)

    log_security_event("FILE_DELETED", admin_user.username, client_ip, "SUCCESS", {"department": department, "filename": safe_filename})
    return {"status": "success", "deleted": safe_filename}

@router.delete("/api/upload/{department}")
@router.delete("/upload/{department}")
def clear_department_documents(
    department: str,
    request: Request,
    admin_user = Depends(require_admin_sudo),
    storage: StorageProvider = Depends(get_storage_provider),
    system = Depends(get_rag_system)
):
    client_ip = request.client.host if request.client else "unknown"
    
    # 1. Clear vectors and KG edges
    system.admin_clear_department(department)

    # 2. Delete raw files
    files = storage.list_files(department)
    for f in files:
        storage.delete_file(department, f)

    log_security_event("DEPARTMENT_DOCS_CLEARED", admin_user.username, client_ip, "SUCCESS", {"department": department, "deleted_count": len(files)})
    return {"status": "success", "message": f"All documents and vectors cleared for department {department}."}
