"""
Parent-Child hierarchical text splitting domain module.
Creates small child chunks (~300 chars) for vector precision and links them to
surrounding parent sections (~1200 chars) for coherent context synthesis.
"""

import os
import uuid
from typing import List, Dict, Any

def create_parent_child_chunks(
    text: str,
    source_file: str = "",
    department: str = "",
    parent_size: int = 1200,
    parent_overlap: int = 200,
    child_size: int = 300,
    child_overlap: int = 50,
    min_role: str = "employee",
    confidentiality: str = "internal"
) -> List[Dict[str, Any]]:
    """
    Creates hierarchical Parent-Child chunks.
    Small child chunks (~300 chars) are stored for high-precision vector search.
    Each child chunk references its surrounding parent section (~1200 chars) for coherent LLM context.
    """
    if not text or not text.strip():
        return []
        
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        parent_splitter = RecursiveCharacterTextSplitter(chunk_size=parent_size, chunk_overlap=parent_overlap)
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=child_size, chunk_overlap=child_overlap)
        parent_docs = parent_splitter.split_text(text)
    except Exception:
        # Fallback pure-Python text splitting if langchain_text_splitters is unavailable
        parent_docs = _simple_text_split(text, chunk_size=parent_size, overlap=parent_overlap)
        child_splitter = None
    
    hierarchical_chunks = []
    
    for p_idx, parent_text in enumerate(parent_docs):
        parent_id = f"{os.path.basename(source_file)}_{p_idx}_{uuid.uuid4().hex[:6]}"
        if child_splitter:
            child_docs = child_splitter.split_text(parent_text)
        else:
            child_docs = _simple_text_split(parent_text, chunk_size=child_size, overlap=child_overlap)
        
        for c_idx, child_text in enumerate(child_docs):
            child_clean = child_text.strip()
            if not child_clean:
                continue
            hierarchical_chunks.append({
                "id": f"{parent_id}_c{c_idx}",
                "text": child_clean,
                "parent_id": parent_id,
                "parent_text": parent_text.strip(),
                "source": source_file,
                "department": department,
                "min_role": min_role,
                "confidentiality": confidentiality
            })
            
    return hierarchical_chunks

def _simple_text_split(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Pure-Python character text splitter with overlap."""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end >= text_len:
            break
        start += (chunk_size - overlap)
    return chunks
