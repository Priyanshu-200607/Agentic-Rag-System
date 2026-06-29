from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from rag_system import MultiDeptRAG
from models import Question, Upload, Login, UserCreate, AccessUpdate
from auth import load_db, save_db
import os
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

uploaded_files_history = load_history()

@app.post("/upload")
async def upload(department: str = Form(...), files: list[UploadFile] = File(...)):
    db = load_db()
    if department not in db["departments"]:
        db["departments"][department] = {"status": "active"}
        save_db(db)
        
    os.makedirs("uploads", exist_ok=True)
    saved_paths = []
    for file in files:
        file_path = os.path.join("uploads", file.filename)
        with open(file_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
        saved_paths.append(file_path)
        uploaded_files_history.append({"filename": file.filename, "department": department})
    
    save_history(uploaded_files_history)

    system.admin_upload_to_department(
        department,
        saved_paths
    )
    return {"status": "success"}

@app.get("/history")
def get_history():
    return {"history": uploaded_files_history}

@app.delete("/upload/{department}/{filename}")
def delete_file(department: str, filename: str):
    file_path = os.path.join("uploads", filename)
    system.admin_delete_file(department, file_path)
    
    global uploaded_files_history
    uploaded_files_history = [
        item for item in uploaded_files_history 
        if not (item["filename"] == filename and item["department"] == department)
    ]
    save_history(uploaded_files_history)
    
    return {"status": "success"}

# --- Admin Endpoints ---
@app.get("/admin/users")
def get_users():
    return load_db()["users"]

@app.post("/admin/users")
def create_user(req: UserCreate):
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
def delete_user(username: str):
    db = load_db()
    if username in db["users"]:
        del db["users"][username]
        save_db(db)
    return {"status": "success"}

@app.put("/admin/users/{username}/suspend")
def toggle_suspend_user(username: str):
    db = load_db()
    if username in db["users"]:
        current = db["users"][username].get("status", "active")
        db["users"][username]["status"] = "suspended" if current == "active" else "active"
        save_db(db)
    return {"status": "success"}

@app.put("/admin/users/{username}/access")
def update_user_access(username: str, req: AccessUpdate):
    db = load_db()
    if username in db["users"]:
        db["users"][username]["allowed_departments"] = req.allowed_departments
        save_db(db)
    return {"status": "success"}

@app.get("/admin/departments")
def get_departments():
    return load_db()["departments"]

@app.post("/admin/departments/{name}")
def create_department(name: str):
    db = load_db()
    if name not in db["departments"]:
        db["departments"][name] = {"status": "active"}
        save_db(db)
    return {"status": "success"}

@app.put("/admin/departments/{name}/suspend")
def toggle_suspend_department(name: str):
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
