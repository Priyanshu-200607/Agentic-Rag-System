"""
Abstract Vector Provider Port (Hexagonal Architecture).
Enables seamless switching between Embedded ChromaDB and Distributed Qdrant / Milvus.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class VectorProvider(ABC):
    """Abstract interface for dense vector databases."""

    @abstractmethod
    def insert_chunks(self, department: str, chunks: List[Dict[str, Any]]) -> int:
        """Inserts chunk dictionaries with embeddings and metadata into department collection."""
        pass

    @abstractmethod
    def query_dense(
        self,
        department: str,
        query_text: str,
        top_k: int = 20,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Executes dense vector search with metadata pre-filtering."""
        pass

    @abstractmethod
    def search_exact_text(
        self,
        department: str,
        keyword: str,
        limit: int = 15,
        allowed_roles: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        """Exact document containment search."""
        pass

    @abstractmethod
    def delete_by_source(self, department: str, source_path: str) -> None:
        """Deletes all chunks originating from a source file."""
        pass

    @abstractmethod
    def delete_department(self, department: str) -> None:
        """Completely drops a department's vector collection."""
        pass
