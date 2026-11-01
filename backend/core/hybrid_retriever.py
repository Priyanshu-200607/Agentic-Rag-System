"""
Hybrid Lexical Search (BM25 Okapi) and Reciprocal Rank Fusion (RRF).
Implements true corpus-wide inverted indexing with disk persistence alongside ChromaDB,
eliminating the pseudo-hybrid flaw where BM25 only rescored top-20 dense matches.
"""

import os
import re
import math
import json
import logging
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger("rag_system")

class BM25Index:
    """
    In-memory BM25 Okapi lexical search index for exact keyword matching and rare identifiers.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = 0
        self.avg_dl = 0.0
        self.doc_lengths = []
        self.doc_freqs = {}   # token -> document count
        self.term_freqs = []  # list of {token: count} for each doc
        self.documents = []   # list of raw documents/metadata

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return re.findall(r'\b\w+\b', text.lower())

    def fit(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.corpus_size = len(documents)
        self.doc_lengths = []
        self.doc_freqs = {}
        self.term_freqs = []
        
        if self.corpus_size == 0:
            return

        total_length = 0
        for doc in documents:
            tokens = self.tokenize(doc.get("text", ""))
            length = len(tokens)
            self.doc_lengths.append(length)
            total_length += length
            
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.term_freqs.append(tf)
            
            for t in set(tokens):
                self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1
                
        self.avg_dl = total_length / self.corpus_size if self.corpus_size > 0 else 1.0

    def get_scores(self, query: str) -> List[float]:
        q_tokens = self.tokenize(query)
        scores = [0.0] * self.corpus_size
        
        for q in q_tokens:
            if q not in self.doc_freqs:
                continue
            df = self.doc_freqs[q]
            idf = math.log(1.0 + (self.corpus_size - df + 0.5) / (df + 0.5))
            
            for idx in range(self.corpus_size):
                tf = self.term_freqs[idx].get(q, 0)
                if tf > 0:
                    doc_len = self.doc_lengths[idx]
                    numerator = tf * (self.k1 + 1.0)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_dl))
                    scores[idx] += idf * (numerator / denominator)
                    
        return scores

    def search(self, query: str, top_n: int = 20) -> List[Dict[str, Any]]:
        if self.corpus_size == 0:
            return []
        scores = self.get_scores(query)
        scored_docs = []
        for idx, score in enumerate(scores):
            if score > 0.0:
                doc_copy = dict(self.documents[idx])
                doc_copy["lexical_score"] = score
                scored_docs.append(doc_copy)
                
        scored_docs.sort(key=lambda x: x["lexical_score"], reverse=True)
        return scored_docs[:top_n]


class CorpusBM25Index:
    """
    True Corpus-Wide Inverted BM25 Index.
    Indexes the complete departmental corpus incrementally, persists token frequencies to disk,
    and supports document-level ABAC pre-filtering during lexical scoring.
    """
    def __init__(self, storage_dir: str = None, k1: float = 1.5, b: float = 0.75):
        self.storage_dir = storage_dir or os.path.join(os.path.dirname(__file__), "bm25_indices")
        self.k1 = k1
        self.b = b
        os.makedirs(self.storage_dir, exist_ok=True)

        # department -> {
        #    "docs": {doc_id: {"text": str, "metadata": dict, "length": int}},
        #    "postings": {token: {doc_id: term_freq}},
        #    "doc_freqs": {token: count},
        #    "total_length": int
        # }
        self.dept_indexes: Dict[str, Dict[str, Any]] = {}

    def _ensure_dept(self, department: str) -> Dict[str, Any]:
        if department not in self.dept_indexes:
            self.dept_indexes[department] = {
                "docs": {},
                "postings": {},
                "doc_freqs": {},
                "total_length": 0
            }
            self._load_dept_from_disk(department)
        return self.dept_indexes[department]

    def _dept_file_path(self, department: str) -> str:
        return os.path.join(self.storage_dir, f"bm25_{department}.json")

    def _save_dept_to_disk(self, department: str):
        dept_data = self.dept_indexes.get(department)
        if not dept_data:
            return
        fpath = self._dept_file_path(department)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(dept_data, f)
        except Exception as e:
            logger.warning(f"[BM25] Failed persisting index for {department}: {e}")

    def _load_dept_from_disk(self, department: str):
        fpath = self._dept_file_path(department)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    self.dept_indexes[department] = json.load(f)
            except Exception as e:
                logger.warning(f"[BM25] Failed loading index for {department}: {e}")

    def add_chunks(self, department: str, chunks: List[Dict[str, Any]]):
        """Incrementally adds document chunks to the corpus-wide inverted index."""
        if not chunks:
            return
        dept = self._ensure_dept(department)
        docs = dept["docs"]
        postings = dept["postings"]
        doc_freqs = dept["doc_freqs"]

        for chunk in chunks:
            chunk_id = chunk.get("id") or str(len(docs))
            text = chunk.get("text", "")
            meta = chunk.get("metadata", {})
            if not meta:
                meta = {
                    "source": chunk.get("source", ""),
                    "department": chunk.get("department", department),
                    "parent_id": chunk.get("parent_id", ""),
                    "parent_text": chunk.get("parent_text", ""),
                    "min_role": chunk.get("min_role", "employee"),
                    "confidentiality": chunk.get("confidentiality", "internal")
                }

            tokens = BM25Index.tokenize(text)
            doc_len = len(tokens)
            
            # Remove previous version if exists
            if chunk_id in docs:
                dept["total_length"] -= docs[chunk_id]["length"]
                # Decrement previous token postings
                for prev_tok in BM25Index.tokenize(docs[chunk_id]["text"]):
                    if prev_tok in postings and chunk_id in postings[prev_tok]:
                        del postings[prev_tok][chunk_id]
                        doc_freqs[prev_tok] = max(0, doc_freqs.get(prev_tok, 1) - 1)

            docs[chunk_id] = {
                "id": chunk_id,
                "text": text,
                "metadata": meta,
                "length": doc_len
            }
            dept["total_length"] += doc_len

            # Build term frequencies
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            for t, count in tf.items():
                if t not in postings:
                    postings[t] = {}
                    doc_freqs[t] = 0
                if chunk_id not in postings[t]:
                    doc_freqs[t] = doc_freqs.get(t, 0) + 1
                postings[t][chunk_id] = count

        self._save_dept_to_disk(department)

    def search(
        self,
        department: str,
        query: str,
        top_n: int = 50,
        allowed_roles: Optional[Set[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes true corpus-wide BM25 Okapi search over the complete department inverted index.
        """
        dept = self._ensure_dept(department)
        docs = dept["docs"]
        postings = dept["postings"]
        doc_freqs = dept["doc_freqs"]
        num_docs = len(docs)
        if num_docs == 0:
            return []

        avg_dl = dept["total_length"] / num_docs if num_docs > 0 else 1.0
        q_tokens = BM25Index.tokenize(query)
        doc_scores: Dict[str, float] = {}

        for q in q_tokens:
            if q not in postings:
                continue
            df = doc_freqs.get(q, 0)
            idf = math.log(1.0 + (num_docs - df + 0.5) / (df + 0.5))

            for doc_id, tf in postings[q].items():
                if doc_id not in docs:
                    continue
                # ABAC pre-filtering
                if allowed_roles is not None:
                    doc_min_role = docs[doc_id].get("metadata", {}).get("min_role", "employee")
                    if doc_min_role not in allowed_roles:
                        continue

                doc_len = docs[doc_id]["length"]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / avg_dl))
                doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + (idf * (numerator / denominator))

        scored_candidates = []
        for doc_id, score in doc_scores.items():
            if score > 0.0:
                doc_entry = dict(docs[doc_id])
                doc_entry["lexical_score"] = round(score, 4)
                doc_entry["distance"] = round(1.0 / (1.0 + score), 4)  # synthetic normalized distance
                scored_candidates.append(doc_entry)

        scored_candidates.sort(key=lambda x: x["lexical_score"], reverse=True)
        return scored_candidates[:top_n]

    def delete_by_source(self, department: str, source_path: str):
        dept = self._ensure_dept(department)
        docs_to_del = [doc_id for doc_id, d in dept["docs"].items() if d.get("metadata", {}).get("source") == source_path]
        for doc_id in docs_to_del:
            self._delete_doc(dept, doc_id)
        self._save_dept_to_disk(department)

    def delete_department(self, department: str):
        if department in self.dept_indexes:
            del self.dept_indexes[department]
        fpath = self._dept_file_path(department)
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except OSError:
                pass

    def _delete_doc(self, dept: Dict[str, Any], doc_id: str):
        if doc_id not in dept["docs"]:
            return
        doc_entry = dept["docs"][doc_id]
        dept["total_length"] = max(0, dept["total_length"] - doc_entry["length"])
        tokens = BM25Index.tokenize(doc_entry["text"])
        for t in set(tokens):
            if t in dept["postings"] and doc_id in dept["postings"][t]:
                del dept["postings"][t][doc_id]
                dept["doc_freqs"][t] = max(0, dept["doc_freqs"].get(t, 1) - 1)
        del dept["docs"][doc_id]


_corpus_bm25_instance = None

def get_corpus_bm25_index() -> CorpusBM25Index:
    global _corpus_bm25_instance
    if _corpus_bm25_instance is None:
        _corpus_bm25_instance = CorpusBM25Index()
    return _corpus_bm25_instance


def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]], 
    lexical_results: List[Dict[str, Any]], 
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Fuses dense vector search rankings and BM25 lexical rankings using Reciprocal Rank Fusion (RRF).
    Formula: RRF(d) = sum(1 / (k + rank))
    """
    scores = {}
    docs = {}
    
    # 1. Score dense rankings
    for rank, doc in enumerate(dense_results):
        doc_id = doc.get("id") or doc.get("text", "")[:100]
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
        if doc_id not in docs:
            docs[doc_id] = doc
            
    # 2. Score lexical rankings
    for rank, doc in enumerate(lexical_results):
        doc_id = doc.get("id") or doc.get("text", "")[:100]
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
        if doc_id not in docs:
            docs[doc_id] = doc
            
    # 3. Sort by aggregated RRF score
    fused = []
    for doc_id, rrf_score in scores.items():
        item = dict(docs[doc_id])
        item["rrf_score"] = round(rrf_score, 6)
        fused.append(item)
        
    fused.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused
