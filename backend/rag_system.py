"""
RAG System Orchestrator Facade.
Re-exports MultiDeptRAG and core utilities from core.orchestrator.
"""

from core.orchestrator import (
    MultiDeptRAG,
    determine_document_access_level,
    get_collection_name,
    background_tasks
)
