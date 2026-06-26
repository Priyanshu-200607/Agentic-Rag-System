from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from rag_system import MultiDeptRAG
from models import Question, Upload, Login
from auth import users
import os
import json

app = FastAPI()

# Enable CORS for the frontend
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
    if req.username not in users:
        return {"success": False}
    user = users[req.username]
    if req.password != user["password"]:
        return {"success": False}
    return {
        "success": True,
        "role": user["role"]
    }

@app.post("/chat/{department}")
def chat(department: str, req: Question):
    target_depts = ["hr", "finance", "it"] if department == "admin" else [department]
    answer = system.query(
        req.question,
        target_depts
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

@app.get("/")
def root():
    return FileResponse(os.path.join(frontend_path, "login.html"))

app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
