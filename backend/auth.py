import json
import os

DB_FILE = "db.json"

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
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DB)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)
