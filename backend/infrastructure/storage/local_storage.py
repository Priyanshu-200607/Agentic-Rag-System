"""
Local Disk Storage Provider Adapter.
Stores raw document files on the local filesystem under department folders.
"""

import os
import shutil
from typing import List
from infrastructure.storage.base import StorageProvider
import config

class LocalDiskStorageProvider(StorageProvider):
    """Local disk implementation of StorageProvider."""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or getattr(config, "UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"))
        os.makedirs(self.base_dir, exist_ok=True)

    def _dept_dir(self, department: str) -> str:
        d = os.path.join(self.base_dir, department)
        os.makedirs(d, exist_ok=True)
        return d

    def save_file(self, department: str, filename: str, content: bytes) -> str:
        dept_dir = self._dept_dir(department)
        target_path = os.path.join(dept_dir, os.path.basename(filename))
        with open(target_path, "wb") as f:
            f.write(content)
        return target_path

    def read_file(self, department: str, filename: str) -> bytes:
        target_path = os.path.join(self._dept_dir(department), os.path.basename(filename))
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"File {filename} not found in department {department}")
        with open(target_path, "rb") as f:
            return f.read()

    def delete_file(self, department: str, filename: str) -> bool:
        target_path = os.path.join(self._dept_dir(department), os.path.basename(filename))
        if os.path.exists(target_path):
            os.remove(target_path)
            return True
        return False

    def list_files(self, department: str) -> List[str]:
        dept_dir = self._dept_dir(department)
        if not os.path.exists(dept_dir):
            return []
        return [f for f in os.listdir(dept_dir) if os.path.isfile(os.path.join(dept_dir, f))]

    def get_file_path(self, department: str, filename: str) -> str:
        return os.path.join(self._dept_dir(department), os.path.basename(filename))
