"""
System Status, Hardware Re-Sync & Diagnostics Router (Hexagonal Ingress).
"""

import os
import gc
import psutil
from typing import Optional, List
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from pydantic import BaseModel

from infrastructure.state.base import StateProvider
from api.dependencies import get_state_provider, get_rag_system, require_admin, require_admin_sudo
from platform_runtime.hardware_probe import probe_hardware, write_hardware_profile
from platform_runtime.resource_manager import ResourceManager
from platform_runtime.audit_ledger import log_security_event
import config

try:
    import GPUtil
except ImportError:
    GPUtil = None

router = APIRouter(tags=["System & Hardware"])

class LLMConfigUpdate(BaseModel):
    master_agent: str
    department_agent: str
    temperature: float = 0.0

def get_dir_size(path: str) -> int:
    total_size = 0
    if os.path.exists(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
    return total_size

@router.get("/api/system/status")
@router.get("/admin/system/status")
def get_system_status(admin_user = Depends(require_admin), system = Depends(get_rag_system)):
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()

    gpu_stats = []
    if GPUtil:
        try:
            gpus = GPUtil.getGPUs()
            for g in gpus:
                gpu_stats.append({
                    "id": g.id,
                    "name": g.name,
                    "load": g.load * 100,
                    "memoryUtil": g.memoryUtil * 100,
                    "memoryTotal": g.memoryTotal,
                    "memoryUsed": g.memoryUsed
                })
        except Exception:
            pass

    chroma_path = getattr(config, "CHROMA_DB_PATH", "")
    upload_path = getattr(config, "UPLOAD_DIR", "")
    kg_path = getattr(config, "KG_DB_PATH", "")

    vector_db_size = get_dir_size(chroma_path)
    upload_size = get_dir_size(upload_path)
    kg_db_size = os.path.getsize(kg_path) if os.path.exists(kg_path) else 0

    from core.orchestrator import background_tasks
    cache_count = getattr(system.kg, "get_cache_size", lambda: 0)() if hasattr(system, "kg") and system.kg else 0

    return {
        "hardware": {
            "cpu": cpu,
            "ram_percent": mem.percent,
            "ram_used_gb": mem.used / (1024**3),
            "ram_total_gb": mem.total / (1024**3),
            "gpus": gpu_stats,
            "tier": ResourceManager.get_tier()
        },
        "storage": {
            "vector_db_mb": vector_db_size / (1024**2),
            "uploads_mb": upload_size / (1024**2),
            "kg_db_mb": kg_db_size / (1024**2),
            "cache_items": cache_count
        },
        "background_tasks": background_tasks
    }

@router.post("/api/admin/system/hardware-sync")
def hardware_sync(
    request: Request,
    admin_user = Depends(require_admin_sudo)
):
    client_ip = request.client.host if request.client else "unknown"
    new_profile = write_hardware_profile()
    ResourceManager.reload_config()

    log_security_event("HARDWARE_SYNC_EXECUTED", admin_user.username, client_ip, "SUCCESS", {"tier": new_profile.get("tier")})
    return {
        "status": "success",
        "message": "Hardware re-benchmarked and profile updated successfully.",
        "hardware_profile": new_profile
    }

@router.post("/api/admin/system/cache/clear")
@router.post("/admin/system/cache/clear")
def clear_cache(admin_user = Depends(require_admin), system = Depends(get_rag_system)):
    if system.graph_provider:
        system.graph_provider.invalidate_cache()
    gc.collect()
    return {"status": "success", "message": "Cache cleared."}

@router.get("/api/admin/llm/available")
@router.get("/admin/llm/available")
def get_llm_available(admin_user = Depends(require_admin)):
    try:
        import ollama
        models = ollama.list()
        return {"models": [m["name"] for m in models.get("models", [])]}
    except Exception as e:
        return {"models": [getattr(config, "LLM_MODEL_NAME", "llama3")], "error": str(e)}

@router.get("/api/admin/llm/config")
@router.get("/admin/llm/config")
def get_llm_config(admin_user = Depends(require_admin)):
    return {
        "master_agent": getattr(config, "LLM_MODEL_NAME", "llama3"),
        "department_agent": getattr(config, "LLM_MODEL_NAME", "llama3"),
        "temperature": 0.0
    }

@router.post("/api/admin/llm/config")
@router.post("/admin/llm/config")
def update_llm_config(req: LLMConfigUpdate, admin_user = Depends(require_admin), system = Depends(get_rag_system)):
    system.llm_model_name = req.master_agent
    for agent in system.agents.values():
        agent.llm_model_name = req.department_agent
    return {"status": "success", "config": req.model_dump()}

@router.get("/api/admin/logs")
@router.get("/admin/logs")
def get_admin_logs(type: str = "all", lines: int = 200, admin_user = Depends(require_admin)):
    log_path = os.path.join(getattr(config, "BASE_DIR", os.path.dirname(__file__)), "logs", "security_audit.jsonl")
    if not os.path.exists(log_path):
        return {"logs": []}
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            return {"logs": [l.strip() for l in all_lines[-lines:]]}
    except Exception as e:
        return {"logs": [], "error": str(e)}
