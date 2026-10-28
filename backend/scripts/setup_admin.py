#!/usr/bin/env python3
"""
CLI Administrator Provisioning Utility for Multi-Department RAG.
Sets or rotates the master administrator password, cryptographically hashes it
using PBKDF2-HMAC-SHA256 (600,000 iterations), and marks setup as completed.
"""
import sys
import os
import argparse
import getpass

# Add parent backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import load_db, save_db, hash_password
from audit_logger import log_security_event

def configure_admin_password(password: str, force: bool = False) -> bool:
    if len(password) < 8:
        print("[ERROR] Administrator password must be at least 8 characters long.")
        return False
        
    db = load_db()
    if db.get("setup_completed", False) and not force:
        print("[WARN] Setup has already been completed.")
        print("To reset the administrator password, re-run with --force.")
        return False
        
    db.setdefault("users", {}).setdefault("admin", {
        "role": "admin",
        "status": "active",
        "allowed_departments": ["hr", "finance", "it"]
    })
    
    db["users"]["admin"]["password_hash"] = hash_password(password)
    db["setup_completed"] = True
    save_db(db)
    
    log_security_event("SETUP_ADMIN_CLI", "admin", "127.0.0.1", "SUCCESS", {"forced": force})
    print("[SUCCESS] Master Administrator credentials configured and hashed successfully.")
    print("          Setup status: COMPLETED")
    return True

def main():
    parser = argparse.ArgumentParser(description="Configure Master Administrator Credentials for RAG Platform")
    parser.add_argument("--password", "-p", help="Master administrator password (min 8 chars)")
    parser.add_argument("--force", "-f", action="store_true", help="Force overwrite existing administrator credentials")
    args = parser.parse_args()

    password = args.password or os.environ.get("ADMIN_PASSWORD")
    if not password:
        if sys.stdin.isatty():
            try:
                password = getpass.getpass("Enter new master administrator password (min 8 characters): ")
                confirm = getpass.getpass("Confirm master administrator password: ")
                if password != confirm:
                    print("[ERROR] Passwords do not match.")
                    sys.exit(1)
            except (KeyboardInterrupt, EOFError):
                print("\nOperation cancelled.")
                sys.exit(1)
        else:
            print("[ERROR] Non-interactive shell detected and no password provided.")
            print("Provide password via --password or ADMIN_PASSWORD environment variable.")
            sys.exit(1)

    success = configure_admin_password(password, force=args.force)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
