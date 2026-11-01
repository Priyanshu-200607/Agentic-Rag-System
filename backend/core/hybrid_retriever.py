"""
Hybrid lexical search (BM25 Okapi) and Reciprocal Rank Fusion (RRF).
Pure algorithmic domain logic, decoupled from physical storage.
"""

import math
import re
from typing import List, Dict, Any

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
        """
        Builds BM25 index from a list of dicts [{"text": ..., "metadata": ..., "id": ...}]
        """
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
            # Standard Lucene/BM25 IDF formula
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
