import json
import os
import threading
import config

DB_FILE = config.AUTH_DB_PATH

# Fix #3 (db race condition): A single process-level lock so no two
# concurrent FastAPI requests can read-modify-write db.json simultaneously.
_db_lock = threading.Lock()

DEFAULT_DB = {
    "users": {
        "admin":   {"password": "123", "role": "admin",    "status": "active", "allowed_departments": ["hr", "finance", "it"]},
        "manager": {"password": "123", "role": "manager",  "status": "active", "allowed_departments": ["hr", "finance", "it"]},
        "hr1":     {"password": "123", "role": "employee", "status": "active", "allowed_departments": ["hr", "it"]},
        "hr2":     {"password": "123", "role": "employee", "status": "active", "allowed_departments": ["hr", "finance"]},
        "it1":     {"password": "123", "role": "employee", "status": "active", "allowed_departments": ["it"]},
        "it2":     {"password": "123", "role": "employee", "status": "active", "allowed_departments": ["it"]},
        "fin1":    {"password": "123", "role": "employee", "status": "active", "allowed_departments": ["finance"]},
        "fin2":    {"password": "123", "role": "employee", "status": "active", "allowed_departments": ["finance"]}
    },
    "departments": {
        "hr": {"status": "active"},
        "finance": {"status": "active"},
        "it": {"status": "active"}
    }
}

def load_db():
    with _db_lock:
        if not os.path.exists(DB_FILE):
            _write_db_unsafe(DEFAULT_DB)
        with open(DB_FILE, "r") as f:
            return json.load(f)

def save_db(data):
    with _db_lock:
        _write_db_unsafe(data)

def _write_db_unsafe(data):
    """Write db.json atomically using a temp file swap to prevent partial-write corruption."""
    tmp_path = DB_FILE + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=4)
    # Atomic rename — on Linux this is guaranteed to be atomic
    os.replace(tmp_path, DB_FILE)
