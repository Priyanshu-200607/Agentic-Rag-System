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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
system = MultiDeptRAG()

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
    answer = system.process_request(
        req.question,
        username=req.username
    )
    return {"answer": answer}

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
    
    history = load_history()
    
    for file in files:
        safe_filename = os.path.basename(file.filename)
        file_path = os.path.join(config.UPLOAD_DIR, safe_filename)
        with open(file_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
        saved_paths.append(file_path)
        history.append({"filename": safe_filename, "department": department})

    # Fix #7: Cap history to prevent unbounded RAM and file growth
    if len(history) > config.HISTORY_MAX_ENTRIES:
        del history[:-config.HISTORY_MAX_ENTRIES]

    save_history(history)

    system.admin_upload_to_department(department, saved_paths)
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
    return {"status": "success"}

@app.delete("/upload/{department}")
def clear_department_docs(department: str, x_username: Optional[str] = Header(None)):
    """Wipe ALL documents and KG facts for an entire department in one shot."""
    _require_admin(x_username)

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
    return load_db()["departments"]

@app.post("/admin/departments/{name}")
def create_department(name: str, x_username: Optional[str] = Header(None)):
    _require_admin(x_username)
    if not re.match(r"^[a-zA-Z0-9_-]{2,60}$", name):
        raise HTTPException(status_code=400, detail="Invalid department name. Must be 2-60 alphanumeric characters.")
    
    db = load_db()
    if name not in db["departments"]:
        db["departments"][name] = {"status": "active"}
        save_db(db)
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


@app.get("/")
def root():
    return FileResponse(os.path.join(frontend_path, "login.html"))

app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
