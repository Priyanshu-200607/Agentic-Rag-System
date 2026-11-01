"""
SQLite + NetworkX Knowledge Graph Provider Adapter.
Embeds knowledge graph storage inside SQLite WAL with in-memory graph traversal.
"""

import os
import logging
from typing import List, Optional
from infrastructure.graph.base import GraphProvider

logger = logging.getLogger("rag_system")

class SQLiteGraphProvider(GraphProvider):
    """Local SQLite + NetworkX/Rustworkx implementation of GraphProvider."""

    def __init__(self, kg_instance=None):
        if kg_instance is not None:
            self.kg = kg_instance
        else:
            from kg_system import KnowledgeGraph
            self.kg = KnowledgeGraph()

    def add_edge(self, source: str, relation: str, target: str, department: str = "general", source_file: str = "") -> None:
        self.kg.add_edge(source, relation, target, department=department, source_file=source_file)

    def get_context_for_entities(
        self,
        query: str,
        llm_model: str,
        department: str,
        max_hops: int = 2,
        max_facts: int = 30
    ) -> List[str]:
        return self.kg.get_context_for_entities(
            query,
            llm_model=llm_model,
            department=department,
            max_hops=max_hops,
            max_facts=max_facts
        )

    def search_edges_sql(self, department: str, entity: str, limit: int = 30) -> List[str]:
        try:
            cursor = self.kg.conn.cursor()
            cursor.execute(
                "SELECT source, relation, target FROM edges WHERE department = ? AND (source LIKE ? OR target LIKE ? OR relation LIKE ?) LIMIT ?",
                (department, f"%{entity}%", f"%{entity}%", f"%{entity}%", limit)
            )
            rows = cursor.fetchall()
            return [f"{row[0]} | {row[1]} | {row[2]}" for row in rows]
        except Exception as e:
            logger.warning(f"[GRAPH] SQL edge search warning: {e}")
            return []

    def admin_delete_file(self, file_path: str) -> None:
        self.kg.admin_delete_file(file_path)

    def delete_department(self, department: str) -> None:
        with self.kg._write_lock:
            self.kg.conn.execute("DELETE FROM edges WHERE department = ?", (department,))
            self.kg.conn.commit()
            self.kg.load()
        self.kg.invalidate_cache()

    def prune_duplicates(self) -> int:
        return self.kg.prune_duplicates()

    def invalidate_cache(self) -> None:
        self.kg.invalidate_cache()
