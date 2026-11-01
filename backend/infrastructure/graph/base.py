"""
Abstract Graph Provider Port (Hexagonal Architecture).
Enables seamless switching between Embedded SQLite/NetworkX and Distributed Neo4j / KùzuDB.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

class GraphProvider(ABC):
    """Abstract interface for Knowledge Graph stores and traversals."""

    @abstractmethod
    def add_edge(self, source: str, relation: str, target: str, department: str = "general", source_file: str = "") -> None:
        """Adds a triplet edge to the graph store."""
        pass

    @abstractmethod
    def get_context_for_entities(
        self,
        query: str,
        llm_model: str,
        department: str,
        max_hops: int = 2,
        max_facts: int = 30
    ) -> List[str]:
        """Performs entity extraction and multi-hop graph traversal to return formatted facts."""
        pass

    @abstractmethod
    def search_edges_sql(self, department: str, entity: str, limit: int = 30) -> List[str]:
        """Direct exact/LIKE query over stored edge triplets."""
        pass

    @abstractmethod
    def admin_delete_file(self, file_path: str) -> None:
        """Removes all graph edges extracted from a specific file."""
        pass

    @abstractmethod
    def delete_department(self, department: str) -> None:
        """Removes all graph edges belonging to a department."""
        pass

    @abstractmethod
    def prune_duplicates(self) -> int:
        """Deduplicates semantically identical entity nodes (nightly self-healing)."""
        pass

    @abstractmethod
    def invalidate_cache(self) -> None:
        """Invalidates in-memory entity lookup caches."""
        pass
