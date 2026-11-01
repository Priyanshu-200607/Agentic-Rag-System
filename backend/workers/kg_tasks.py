"""
Knowledge graph background extraction worker task.
"""

import logging
from typing import List, Dict, Any
from infrastructure.graph.base import GraphProvider

logger = logging.getLogger("rag_system")

def run_kg_extraction_task(
    department: str,
    documents: List[str],
    sources: List[str],
    graph_provider: GraphProvider,
    llm_model: str = "llama3"
) -> Dict[str, Any]:
    extracted_count = 0
    raw_kg = getattr(graph_provider, "kg", None)
    if not raw_kg:
        return {"status": "skipped", "reason": "No KG instance"}

    for doc, src in zip(documents, sources):
        try:
            raw_kg.build_from_text(doc, llm_model_name=llm_model, source_file=src, department=department)
            extracted_count += 1
        except Exception as e:
            logger.error(f"[KG WORKER] Extraction failed for {src}: {e}")

    return {
        "department": department,
        "documents_processed": extracted_count
    }
