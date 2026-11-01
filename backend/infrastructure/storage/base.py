"""
Abstract Storage Provider Port (Hexagonal Architecture).
Enables seamless switching between Local Disk and AWS S3 / MinIO.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

class StorageProvider(ABC):
    """Abstract interface for raw document and blob storage."""
    
    @abstractmethod
    def save_file(self, department: str, filename: str, content: bytes) -> str:
        """Saves file content to destination. Returns stored path or URI."""
        pass

    @abstractmethod
    def read_file(self, department: str, filename: str) -> bytes:
        """Reads file bytes from storage."""
        pass

    @abstractmethod
    def delete_file(self, department: str, filename: str) -> bool:
        """Deletes a file from storage."""
        pass

    @abstractmethod
    def list_files(self, department: str) -> List[str]:
        """Lists file names stored for a given department."""
        pass

    @abstractmethod
    def get_file_path(self, department: str, filename: str) -> str:
        """Returns local filesystem path or temporary accessible path for processing."""
        pass
