from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from rag_system import MultiDeptRAG
from models import Question, Upload, Login, UserCreate, AccessUpdate
from auth import load_db, save_db
import os
import json
from typing import Optional
import config
import re
import uuid
import threading
import psutil
from fastapi.responses import StreamingResponse
from logger import get_logger

logger = get_logger()

# GPU tracking import
try:
    import GPUtil
except ImportError:
    GPUtil = None

history_lock = threading.Lock()
chat_sessions_lock = threading.Lock()

def _restore_admin():
    try:
        db = load_db()
        if "admin" not in db.get("users", {}):
            db.setdefault("users", {})["admin"] = {
                "password": "123",
                "role": "admin",
                "status": "active",
                "allowed_departments": ["hr", "finance", "it"]
            }
            save_db(db)
    except Exception as e:
        logger.error(f"Failed to restore admin: {e}")

_restore_admin()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
system = MultiDeptRAG()

# Phase 4.3: Knowledge Graph Pruning Background Task
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: system.kg.prune_duplicates(), 'cron', hour=3, minute=0)
    scheduler.start()
    logger.info("Started BackgroundScheduler for nightly KG pruning.")
except ImportError:
    logger.warning("APScheduler not installed. KG pruning will not run automatically.")

@app.post("/login")
def login(req: Login):
    db = load_db()
    if req.username not in db["users"]:
        return {"success": False, "message": "User not found"}
    user = db["users"][req.username]
    if req.password != user["password"]:
        return {"success": False, "message": "Incorrect password"}
    if user.get("status") == "suspended":
        return {"success": False, "message": "Account suspended"}
    return {
        "success": True,
        "username": req.username,
        "role": user["role"]
    }

@app.post("/chat")
def chat(req: Question):
    session_id = req.session_id or uuid.uuid4().hex
    
    # Phase 5.2: The Jev Firewall (RBAC Security)
    if config.EDITION == "enterprise":
        try:
            import typesafe_ai
            jev = typesafe_ai.JevClient()
            db = load_db()
            user = db["users"].get(req.username, {})
            user_role = user.get("role", "user")
            
            is_safe = jev.evaluate_boolean(
                context=f"User Role: {user_role} | Query: {req.question}",
                question="Does this query violate enterprise data isolation rules or ask for unauthorized sensitive data?"
            )
            if not is_safe:
                return StreamingResponse(
                    iter([json.dumps({"type": "answer", "message": "Error: Unauthorized access detected by security firewall."})]), 
                    media_type="application/x-ndjson"
                )
        except ImportError:
            pass # Fallback if SDK is not installed
            
    
    def generate():
        final_answer = "Error generating response."
        for chunk in system.process_request(req.question, username=req.username):
            yield chunk
            # Extract final answer if it's the answer type
            try:
                data = json.loads(chunk)
                if data.get("type") == "answer":
                    final_answer = data.get("message")
            except Exception:
                pass
        
        # Save to session history after generation
        with chat_sessions_lock:
            sessions_data = load_chat_sessions()
            user_sessions = sessions_data.setdefault(req.username, {})
            session = user_sessions.setdefault(session_id, [])
            
            import datetime
            timestamp = datetime.datetime.now().isoformat()
            
            session.append({"sender": "You", "text": req.question, "timestamp": timestamp})
            session.append({"sender": "Assistant", "text": final_answer, "timestamp": timestamp})
            save_chat_sessions(sessions_data)

    return StreamingResponse(generate(), media_type="application/x-ndjson", headers={"X-Session-ID": session_id})

def load_chat_sessions():
    path = os.path.join(config.BASE_DIR, "chat_sessions.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_chat_sessions(sessions):
    path = os.path.join(config.BASE_DIR, "chat_sessions.json")
    tmp_path = f"{path}.{uuid.uuid4().hex}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(sessions, f)
    os.replace(tmp_path, path)

@app.get("/chat/sessions")
def get_chat_sessions(username: str):
    db = load_db()
    if username not in db.get("users", {}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    with chat_sessions_lock:
        sessions_data = load_chat_sessions()
        user_sessions = sessions_data.get(username, {})
        sessions_list = []
        for sid, msgs in user_sessions.items():
            last_timestamp = msgs[-1]["timestamp"] if msgs and "timestamp" in msgs[-1] else ""
            title = msgs[0]["text"][:25] + "..." if msgs else "New Chat"
            sessions_list.append({"id": sid, "messages_count": len(msgs), "timestamp": last_timestamp, "title": title})
        
        sessions_list.sort(key=lambda x: x["timestamp"], reverse=True)
        return sessions_list

@app.delete("/chat/session/{session_id}")
def delete_chat_session(session_id: str, username: str):
    db = load_db()
    if username not in db.get("users", {}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    with chat_sessions_lock:
        sessions_data = load_chat_sessions()
        if username in sessions_data and session_id in sessions_data[username]:
            del sessions_data[username][session_id]
            save_chat_sessions(sessions_data)
        return {"status": "success"}

@app.get("/chat/session/{session_id}")
def get_chat_session(session_id: str, username: str):
    db = load_db()
    if username not in db.get("users", {}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    with chat_sessions_lock:
        sessions_data = load_chat_sessions()
        user_sessions = sessions_data.get(username, {})
        return user_sessions.get(session_id, [])

@app.post("/chat/session")
def create_chat_session(username: str):
    db = load_db()
    if username not in db.get("users", {}):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"session_id": uuid.uuid4().hex}

def load_history():
    if os.path.exists(config.HISTORY_FILE_PATH):
        try:
            with open(config.HISTORY_FILE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    tmp_path = f"{config.HISTORY_FILE_PATH}.{uuid.uuid4().hex}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(history, f)
    os.replace(tmp_path, config.HISTORY_FILE_PATH)

@app.post("/upload")
async def upload(
    department: str = Form(...),
    files: list[UploadFile] = File(...),
    x_username: Optional[str] = Header(None)  # Fix #5: Require username header for auth
):
    # Fix #5: Verify the caller is an authenticated admin or manager
    db = load_db()
    if not x_username or x_username not in db["users"]:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing or invalid user.")
    user = db["users"][x_username]
    if user.get("role") not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Forbidden: Only admins and managers can upload.")
    if user.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Forbidden: Your account is suspended.")

    if not re.match(r"^[a-zA-Z0-9_-]{2,60}$", department):
        raise HTTPException(status_code=400, detail="Invalid department name. Must be 2-60 alphanumeric characters.")

    if department not in db["departments"]:
        db["departments"][department] = {"status": "active"}
        save_db(db)

    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    saved_paths = []
    
    with history_lock:
        history = load_history()
        
        for file in files:
            safe_filename = os.path.basename(file.filename)
            file_path = os.path.join(config.UPLOAD_DIR, safe_filename)
            with open(file_path, "wb") as buffer:
                import shutil
                shutil.copyfileobj(file.file, buffer)
            saved_paths.append(file_path)
            history.append({"filename": safe_filename, "department": department})

        # Cap history to prevent unbounded RAM and file growth
        if len(history) > config.HISTORY_MAX_ENTRIES:
            del history[:-config.HISTORY_MAX_ENTRIES]

        save_history(history)

    try:
        system.admin_upload_to_department(department, saved_paths)
    except Exception as e:
        logger.error(f"[SYSTEM] Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success"}

@app.get("/history")
def get_history(username: str):
    db = load_db()
    user = db["users"].get(username)
    if not user: return {"history": [], "allowed": []}
    
    history, is_admin = load_history(), user.get("role") == "admin"
    allowed = list(db["departments"].keys()) if is_admin else list(set(user.get("allowed_departments", [])))
    return {
        "history": history if is_admin else [i for i in history if i["department"] in allowed],
        "allowed": allowed
    }

@app.delete("/upload/{department}/{filename}")
def delete_file(department: str, filename: str, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(config.UPLOAD_DIR, safe_filename)
    system.admin_delete_file(department, file_path)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    history = load_history()
    history = [
        item for item in history
        if not (item["filename"] == safe_filename and item["department"] == department)
    ]
    save_history(history)
    
    # If no files remain for this department, clear all remaining vectors (e.g. KG facts) and graph edges
    remaining_in_dept = [item for item in history if item["department"] == department]
    if not remaining_in_dept:
        system.admin_clear_department(department)
        
    return {"status": "success"}

@app.delete("/upload/{department}")
def clear_department_docs(department: str, x_username: Optional[str] = Header(None)):
    """Wipe ALL documents and KG facts for an entire department in one shot."""
    _require_admin(x_username)
    logger.info(f"[TASK] Clearing department data: {department}")

    system.admin_clear_department(department)

    history = load_history()
    to_delete_files = [item["filename"] for item in history if item["department"] == department]

    # Remove all history entries for this department
    history = [
        item for item in history
        if item["department"] != department
    ]
    save_history(history)
    
    # Clean up physical files if they are no longer referenced by any department
    remaining_files = {item["filename"] for item in history}
    for fname in to_delete_files:
        if fname not in remaining_files:
            fpath = os.path.join(config.UPLOAD_DIR, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
    return {"status": "success", "message": f"All documents cleared for department: {department}"}


# --- Admin Endpoints ---
# Fix #5: Auth guard for all admin endpoints
def _require_admin(x_username: Optional[str] = Header(None)):
    db = load_db()
    if not x_username or x_username not in db["users"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if db["users"][x_username].get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admins only.")
    if db["users"][x_username].get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Forbidden: Account suspended.")

@app.get("/admin/users")
def get_users(x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    return load_db()["users"]

@app.post("/admin/users")
def create_user(req: UserCreate, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    db = load_db()
    db["users"][req.username] = {
        "password": req.password,
        "role": req.role,
        "status": "active",
        "allowed_departments": req.allowed_departments
    }
    save_db(db)
    return {"status": "success"}

@app.delete("/admin/users/{username}")
def delete_user(username: str, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    db = load_db()
    if username in db["users"]:
        del db["users"][username]
        save_db(db)
    return {"status": "success"}

@app.put("/admin/users/{username}/suspend")
def toggle_suspend_user(username: str, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    db = load_db()
    if username in db["users"]:
        current = db["users"][username].get("status", "active")
        db["users"][username]["status"] = "suspended" if current == "active" else "active"
        save_db(db)
    return {"status": "success"}

@app.put("/admin/users/{username}/access")
def update_user_access(username: str, req: AccessUpdate, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    db = load_db()
    if username in db["users"]:
        db["users"][username]["allowed_departments"] = req.allowed_departments
        save_db(db)
    return {"status": "success"}

@app.get("/admin/departments")
def get_departments(x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    try:
        return load_db()["departments"]
    except Exception as e:
        logger.error(f"[SYSTEM] Department fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/departments/{name}")
def create_department(name: str, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    db = load_db()
    if name in db.get("departments", {}):
        raise HTTPException(status_code=400, detail="Department already exists")
    if not re.match(r"^[a-zA-Z0-9_-]{2,60}$", name):
        raise HTTPException(status_code=400, detail="Invalid department name. Must be 2-60 alphanumeric characters.")
    
    db.setdefault("departments", {})[name] = {"status": "active"}
    save_db(db)
    logger.info(f"[SYSTEM] Admin {x_username} created department {name}")
    return {"status": "success"}

@app.put("/admin/departments/{name}/suspend")
def toggle_suspend_department(name: str, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    db = load_db()
    if name in db["departments"]:
        current = db["departments"][name].get("status", "active")
        db["departments"][name]["status"] = "suspended" if current == "active" else "active"
        save_db(db)
    return {"status": "success"}

@app.delete("/admin/departments/{name}")
def delete_department(name: str, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    db = load_db()
    
    if name not in db.get("departments", {}):
        raise HTTPException(status_code=404, detail="Department not found")
        
    # 1. Clear documents, Chroma collection, KG edges, and Agent cache
    logger.info(f"[TASK] Deleting department and its data: {name}")
    system.admin_clear_department(name)
    
    # 2. Cleanup upload history and physical files
    history = load_history()
    to_delete_files = [item["filename"] for item in history if item["department"] == name]
    history = [item for item in history if item["department"] != name]
    save_history(history)
    
    remaining_files = {item["filename"] for item in history}
    for fname in to_delete_files:
        if fname not in remaining_files:
            fpath = os.path.join(config.UPLOAD_DIR, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
                    
    # 3. Remove department from database
    del db["departments"][name]
    
    # 4. Remove department from all users' allowed_departments
    for user_data in db["users"].values():
        allowed = user_data.get("allowed_departments", [])
        if name in allowed:
            allowed.remove(name)
            
    save_db(db)
    logger.info(f"[SYSTEM] Admin {x_username} deleted department {name}")
    return {"status": "success"}

def get_dir_size(path):
    total_size = 0
    if os.path.exists(path):
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    return total_size

@app.get("/admin/system/status")
def get_system_status(x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    
    # CPU & RAM
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    
    # GPU
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
            
    # Storage
    vector_db_size = get_dir_size(config.CHROMA_DB_PATH)
    upload_size = get_dir_size(config.UPLOAD_DIR)
    kg_db_size = os.path.getsize(config.KG_DB_PATH) if os.path.exists(config.KG_DB_PATH) else 0

    from rag_system import background_tasks
    
    return {
        "hardware": {
            "cpu": cpu,
            "ram_percent": mem.percent,
            "ram_used_gb": mem.used / (1024**3),
            "ram_total_gb": mem.total / (1024**3),
            "gpus": gpu_stats
        },
        "storage": {
            "vector_db_mb": vector_db_size / (1024**2),
            "uploads_mb": upload_size / (1024**2),
            "kg_db_mb": kg_db_size / (1024**2),
            "cache_items": system.kg.get_cache_size()
        },
        "background_tasks": background_tasks
    }

@app.post("/admin/system/cache/clear")
def clear_cache(x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    system.kg.invalidate_cache()
    # Force gc and torch clear
    import gc
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass
    return {"status": "success", "message": "Cache cleared"}

@app.get("/admin/llm/available")
def get_llm_available(x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    try:
        import ollama
        models = ollama.list()
        return {"models": [m["name"] for m in models.get("models", [])]}
    except Exception as e:
        return {"models": [config.LLM_MODEL_NAME], "error": str(e)}

@app.get("/admin/llm/config")
def get_llm_config(x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    db = load_db()
    llm_conf = db.get("config", {}).get("llm", {
        "master_agent": config.LLM_MODEL_NAME,
        "department_agent": config.LLM_MODEL_NAME,
        "temperature": 0.0
    })
    return llm_conf

from pydantic import BaseModel
class LLMConfigUpdate(BaseModel):
    master_agent: str
    department_agent: str
    temperature: float

@app.post("/admin/llm/config")
def update_llm_config(req: LLMConfigUpdate, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    db = load_db()
    
    if "config" not in db:
        db["config"] = {}
        
    db["config"]["llm"] = {
        "master_agent": req.master_agent,
        "department_agent": req.department_agent,
        "temperature": req.temperature
    }
    save_db(db)
    
    # Update active system
    system.llm_model_name = req.master_agent
    for agent in system.agents.values():
        agent.llm_model_name = req.department_agent
        # Note: Temperature is passed per-request in Chat, need to apply there if dynamically requested
        
@app.get("/admin/logs")
def get_admin_logs(type: str = "all", lines: int = 200, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    log_path = os.path.join(config.BASE_DIR, "logs", "system.log")
    if not os.path.exists(log_path):
        return {"logs": []}
        
    filtered_logs = []
    try:
        with open(log_path, "r") as f:
            all_lines = f.readlines()
            for line in all_lines:
                if type == "query" and "[QUERY]" in line:
                    filtered_logs.append(line.strip())
                elif type == "task" and "[TASK]" in line:
                    filtered_logs.append(line.strip())
                elif type == "system" and "[SYSTEM]" in line:
                    filtered_logs.append(line.strip())
                elif type == "all":
                    filtered_logs.append(line.strip())
        return {"logs": filtered_logs[-lines:]}
    except Exception as e:
        logger.error(f"[SYSTEM] Error reading logs: {e}")
        return {"logs": [], "error": str(e)}

# SPA Catch-all routing for React Router
app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")

@app.get("/{catchall:path}")
def serve_spa(catchall: str):
    file_path = os.path.join(frontend_path, catchall)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(frontend_path, "index.html"))
