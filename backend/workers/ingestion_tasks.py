"""
Document ingestion background worker task.
Executes document parsing, chunking, and embedding off the main web thread.
"""

import logging
from typing import List, Dict, Any
from core.document_processor import process_file, determine_document_access_level
from core.chunking import create_parent_child_chunks
from infrastructure.vector.base import VectorProvider

logger = logging.getLogger("rag_system")

def run_ingestion_task(
    department: str,
    file_paths: List[str],
    vector_provider: VectorProvider,
    chunk_size: int = 1200,
    overlap: int = 200
) -> Dict[str, Any]:
    """Processes document files and indexes chunks into the vector provider."""
    total_chunks = 0
    processed_files = []

    for path in file_paths:
        try:
            text = process_file(path)
            if not text.strip():
                continue
            confidentiality, min_role = determine_document_access_level(path)
            chunks = create_parent_child_chunks(
                text=text,
                source_file=path,
                department=department,
                parent_size=chunk_size,
                parent_overlap=overlap,
                child_size=300,
                child_overlap=50,
                min_role=min_role,
                confidentiality=confidentiality
            )
            if chunks:
                vector_provider.insert_chunks(department, chunks)
                total_chunks += len(chunks)
                processed_files.append(path)
        except Exception as e:
            logger.error(f"[WORKER] Failed ingesting {path}: {e}")

    return {
        "department": department,
        "files_processed": len(processed_files),
        "total_chunks": total_chunks
    }
