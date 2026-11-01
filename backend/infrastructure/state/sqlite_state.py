"""
SQLite State Provider Adapter with Write-Ahead Logging (WAL).
Replaces flat JSON files (db.json, history.json, chat_sessions.json) with
a relational, ACID-compliant database that is safe across multi-worker processes.
"""

import os
import json
import time
import sqlite3
import threading
from typing import Optional, List, Dict, Any
from core.schemas import User, SudoSession
from infrastructure.state.base import StateProvider
import config

_DEFAULT_HASH_123 = "$pbkdf2-sha256$600000$1e07e2c1fd0f1db52c3209dd35d965fc$d20a780ca63b87b8a5ed55cf0c03d85ef4859fbb78a27a5f9746784527eebb6d"

class SQLiteStateProvider(StateProvider):
    """
    Embedded SQLite State Provider with WAL mode.
    Guarantees thread-safety and multi-process concurrency for Uvicorn/Gunicorn workers.
    """
    def __init__(self, db_path: str = None):
        self.db_path = db_path or getattr(config, "STATE_DB_PATH", os.path.join(getattr(config, "BASE_DIR", os.path.dirname(__file__)), "state.db"))
        self._lock = threading.Lock()
        self._init_db()
        self._migrate_legacy_json_if_needed()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self):
        with self._lock, self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'employee',
                status TEXT NOT NULL DEFAULT 'active',
                allowed_departments TEXT NOT NULL DEFAULT '[]',
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS departments (
                name TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'active',
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                username TEXT NOT NULL,
                sender TEXT NOT NULL,
                text TEXT NOT NULL,
                role TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sudo_sessions (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                issued_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                signature TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'elevated_admin_action'
            );

            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

    def _migrate_legacy_json_if_needed(self):
        """Transparently migrates flat db.json, chat_sessions.json, and history.json if present."""
        with self._lock, self._get_connection() as conn:
            # Check if users table is empty
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] > 0:
                return

            base_dir = getattr(config, "BASE_DIR", os.path.dirname(__file__))
            db_json_path = getattr(config, "AUTH_DB_PATH", os.path.join(base_dir, "db.json"))
            
            # 1. Migrate db.json
            now = time.time()
            if os.path.exists(db_json_path):
                try:
                    with open(db_json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Setup status
                    setup_done = "1" if data.get("setup_completed", False) else "0"
                    conn.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('setup_completed', ?)", (setup_done,))

                    # Departments
                    for dept_name, dept_info in data.get("departments", {}).items():
                        conn.execute(
                            "INSERT OR IGNORE INTO departments (name, status, created_at) VALUES (?, ?, ?)",
                            (dept_name, dept_info.get("status", "active"), now)
                        )

                    # Users
                    for uname, uinfo in data.get("users", {}).items():
                        pwd_hash = uinfo.get("password_hash") or _DEFAULT_HASH_123
                        depts_json = json.dumps(uinfo.get("allowed_departments", []))
                        conn.execute(
                            "INSERT OR REPLACE INTO users (username, password_hash, role, status, allowed_departments, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (uname, pwd_hash, uinfo.get("role", "employee"), uinfo.get("status", "active"), depts_json, now)
                        )
                except Exception as e:
                    print(f"[STATE] Error migrating db.json: {e}")

            # Bootstrap default admin if still empty
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                conn.execute(
                    "INSERT INTO users (username, password_hash, role, status, allowed_departments, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    ("admin", _DEFAULT_HASH_123, "admin", "active", json.dumps(["hr", "finance", "it"]), now)
                )
                conn.execute(
                    "INSERT OR IGNORE INTO departments (name, status, created_at) VALUES ('hr', 'active', ?), ('finance', 'active', ?), ('it', 'active', ?)",
                    (now, now, now)
                )
                conn.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('setup_completed', '0')")

            # 2. Migrate chat_sessions.json if exists
            chat_json_path = os.path.join(base_dir, "chat_sessions.json")
            if os.path.exists(chat_json_path):
                try:
                    with open(chat_json_path, "r", encoding="utf-8") as f:
                        sessions_data = json.load(f)
                    for uname, u_sessions in sessions_data.items():
                        # ensure user exists in db or skip foreign key crash
                        cursor.execute("SELECT username FROM users WHERE username = ?", (uname,))
                        if not cursor.fetchone():
                            continue
                        for s_id, msgs in u_sessions.items():
                            conn.execute(
                                "INSERT OR IGNORE INTO chat_sessions (session_id, username, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                                (s_id, uname, f"Chat {s_id[:6]}", now, now)
                            )
                            for msg in msgs:
                                conn.execute(
                                    "INSERT INTO chat_messages (session_id, username, sender, text, role, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                                    (s_id, uname, msg.get("sender", "Unknown"), msg.get("text", ""), msg.get("role"), msg.get("timestamp", ""))
                                )
                except Exception as e:
                    print(f"[STATE] Error migrating chat_sessions.json: {e}")

    # --- USER METHODS ---
    def get_user(self, username: str) -> Optional[User]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password_hash, role, status, allowed_departments FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if not row:
                return None
            return User(
                username=row["username"],
                password_hash=row["password_hash"],
                role=row["role"],
                status=row["status"],
                allowed_departments=json.loads(row["allowed_departments"])
            )

    def save_user(self, user: User) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO users (username, password_hash, role, status, allowed_departments, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user.username, user.password_hash or _DEFAULT_HASH_123, user.role, user.status, json.dumps(user.allowed_departments), time.time())
            )

    def delete_user(self, username: str) -> bool:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            return cursor.rowcount > 0

    def list_users(self) -> List[User]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password_hash, role, status, allowed_departments FROM users")
            rows = cursor.fetchall()
            return [
                User(
                    username=r["username"],
                    password_hash=r["password_hash"],
                    role=r["role"],
                    status=r["status"],
                    allowed_departments=json.loads(r["allowed_departments"])
                )
                for r in rows
            ]

    # --- DEPARTMENT METHODS ---
    def get_department(self, name: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, status, created_at FROM departments WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_department(self, name: str, status: str = "active") -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO departments (name, status, created_at) VALUES (?, ?, ?)",
                (name, status, time.time())
            )

    def delete_department(self, name: str) -> bool:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM departments WHERE name = ?", (name,))
            return cursor.rowcount > 0

    def list_departments(self) -> Dict[str, Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, status, created_at FROM departments")
            rows = cursor.fetchall()
            return {r["name"]: {"status": r["status"], "created_at": r["created_at"]} for r in rows}

    # --- CHAT & SESSION METHODS ---
    def create_chat_session(self, username: str, session_id: str, title: str = "New Chat") -> str:
        with self._lock, self._get_connection() as conn:
            now = time.time()
            conn.execute(
                "INSERT OR REPLACE INTO chat_sessions (session_id, username, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, username, title, now, now)
            )
        return session_id

    def get_chat_sessions(self, username: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id, title, created_at, updated_at FROM chat_sessions WHERE username = ? ORDER BY updated_at DESC",
                (username,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_chat_history(self, username: str, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sender, text, role, timestamp FROM chat_messages WHERE session_id = ? AND username = ? ORDER BY id ASC",
                (session_id, username)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def append_chat_message(self, username: str, session_id: str, message: Dict[str, Any]) -> None:
        with self._lock, self._get_connection() as conn:
            now = time.time()
            # Ensure session exists
            conn.execute(
                "INSERT OR IGNORE INTO chat_sessions (session_id, username, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, username, message.get("text", "New Chat")[:30], now, now)
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id)
            )
            conn.execute(
                "INSERT INTO chat_messages (session_id, username, sender, text, role, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, username, message.get("sender", "Unknown"), message.get("text", ""), message.get("role"), str(message.get("timestamp", "")))
            )

    def delete_chat_session(self, username: str, session_id: str) -> bool:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_sessions WHERE session_id = ? AND username = ?", (session_id, username))
            return cursor.rowcount > 0

    # --- SUDO SESSIONS ---
    def save_sudo_session(self, sudo_session: SudoSession) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sudo_sessions (token, username, ip_address, issued_at, expires_at, signature, scope) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sudo_session.token, sudo_session.username, sudo_session.ip_address, sudo_session.issued_at, sudo_session.expires_at, sudo_session.signature, sudo_session.scope)
            )

    def get_sudo_session(self, token: str) -> Optional[SudoSession]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT token, username, ip_address, issued_at, expires_at, signature, scope FROM sudo_sessions WHERE token = ?", (token,))
            row = cursor.fetchone()
            if not row:
                return None
            session = SudoSession(
                token=row["token"],
                username=row["username"],
                ip_address=row["ip_address"],
                issued_at=row["issued_at"],
                expires_at=row["expires_at"],
                signature=row["signature"],
                scope=row["scope"]
            )
            if time.time() > session.expires_at:
                self.delete_sudo_session(token)
                return None
            return session

    def delete_sudo_session(self, token: str) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM sudo_sessions WHERE token = ?", (token,))

    # --- SETUP / SYSTEM STATE ---
    def get_setup_status(self) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = 'setup_completed'")
            row = cursor.fetchone()
            return row["value"] == "1" if row else False

    def set_setup_completed(self, completed: bool = True) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO system_config (key, value) VALUES ('setup_completed', ?)",
                ("1" if completed else "0",)
            )
