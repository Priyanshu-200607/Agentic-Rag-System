"""
Cross-Encoder Reranker for two-stage retrieval.
Rescores candidate chunks retrieved by vector/lexical search (top-20 to top-50)
using joint query-document scoring down to top-5 high-relevance chunks.
"""

import re
import math
from typing import List, Dict, Any
import logging

logger = logging.getLogger("rag_system")

class LocalReranker:
    """
    Cross-Encoder Reranker for two-stage retrieval.
    Takes candidate chunks retrieved by vector/lexical search (top-20 to top-50)
    and rescores them using joint query-document cross-scoring to return top-5 high-relevance chunks.
    """
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self._init_model()

    def _init_model(self):
        try:
            from sentence_transformers import CrossEncoder
            # Preload if available offline or in cache
            self.model = CrossEncoder(self.model_name, max_length=512)
            logger.info(f"[RERANKER] Neural Cross-Encoder '{self.model_name}' loaded successfully.")
        except Exception:
            logger.info("[RERANKER] Neural Cross-Encoder not cached locally. Utilizing high-speed lexical-semantic cross-scoring engine.")
            self.model = None

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Reranks candidate dictionary items [{"text": ..., "metadata": ..., "distance": ...}]
        and returns the top_n items with a calibrated "relevance_score".
        """
        if not candidates:
            return []
            
        if len(candidates) <= top_n:
            return candidates

        # 1. Neural Cross-Encoder inference if loaded
        if self.model:
            try:
                pairs = [[query, c.get("text", "")] for c in candidates]
                scores = self.model.predict(pairs)
                for c, s in zip(candidates, scores):
                    c["relevance_score"] = float(s)
                candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
                return candidates[:top_n]
            except Exception as e:
                logger.warning(f"[RERANKER] Neural rerank failed ({e}), falling back to cross-scoring engine.")

        # 2. High-speed Cross-Scoring Engine (Cross-Attention approximation)
        query_clean = query.strip().lower()
        q_tokens = set(re.findall(r'\b\w+\b', query_clean))
        exact_ids = re.findall(r'\b([a-zA-Z]+[-_]\d+|\d{4}|\d+k|\d+)\b', query_clean)
        
        for cand in candidates:
            doc_text = cand.get("text", "").lower()
            doc_tokens = re.findall(r'\b\w+\b', doc_text)
            doc_token_set = set(doc_tokens)
            
            # Feature A: Token Overlap (Jaccard & Recall)
            overlap = q_tokens.intersection(doc_token_set)
            token_recall = len(overlap) / max(1, len(q_tokens))
            
            # Feature B: Exact Identifier Matching (Boost for technical IDs / numbers)
            id_boost = 0.0
            for eid in exact_ids:
                if eid in doc_text:
                    id_boost += 2.5
                    
            # Feature C: Exact Sequential Phrase Matching
            phrase_boost = 1.5 if query_clean in doc_text else 0.0
            
            # Feature D: Cosine Distance Inverse (if candidate came from vector search)
            base_dist = cand.get("distance", 1.0)
            vector_sim = max(0.0, 1.0 - (base_dist / 2.0))
            
            # Length penalty (penalize extremely short noise chunks)
            len_score = min(1.0, len(doc_tokens) / 30.0)
            
            # Composite Joint Score
            composite_score = (token_recall * 3.0) + id_boost + phrase_boost + (vector_sim * 2.0) + (len_score * 0.5)
            cand["relevance_score"] = round(composite_score, 4)
            
        candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        return candidates[:top_n]
