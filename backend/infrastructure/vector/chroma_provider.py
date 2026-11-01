"""
ChromaDB Vector Provider Adapter.
Manages multi-collection embedded ChromaDB storage with SentenceTransformer embeddings.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from infrastructure.vector.base import VectorProvider
import config

logger = logging.getLogger("rag_system")

class ChromaVectorProvider(VectorProvider):
    """Local ChromaDB implementation of VectorProvider."""

    def __init__(self, db_path: str = None, embed_model=None, embed_model_name: str = None):
        self.db_path = db_path or getattr(config, "CHROMA_DB_PATH", os.path.join(getattr(config, "BASE_DIR", os.path.dirname(__file__)), "chroma_db_multi"))
        self.embed_model_name = embed_model_name or getattr(config, "EMBED_MODEL_NAME", "BAAI/bge-small-en-v1.5")
        
        # Initialize Chroma PersistentClient
        import chromadb
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Initialize Embed Model if not provided
        if embed_model is not None:
            self.embed_model = embed_model
        else:
            try:
                from sentence_transformers import SentenceTransformer
                from platform_runtime.resource_manager import ResourceManager
                self.embed_model = SentenceTransformer(self.embed_model_name, device=ResourceManager.get_device())
            except Exception as e:
                logger.warning(f"[CHROMA] SentenceTransformer initialization note: {e}")
                self.embed_model = None

    def _collection_name(self, department: str) -> str:
        return f"dept_{department}"

    def get_or_create_collection(self, department: str):
        return self.client.get_or_create_collection(name=self._collection_name(department))

    def insert_chunks(self, department: str, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
        collection = self.get_or_create_collection(department)
        
        texts = [c["text"] for c in chunks]
        ids = [c["id"] for c in chunks]
        metadatas = []
        for c in chunks:
            meta = {
                "source": c.get("source", ""),
                "department": c.get("department", department),
                "parent_id": c.get("parent_id", ""),
                "parent_text": c.get("parent_text", ""),
                "min_role": c.get("min_role", "employee"),
                "confidentiality": c.get("confidentiality", "internal")
            }
            metadatas.append(meta)

        if self.embed_model:
            embeddings = self.embed_model.encode(texts).tolist()
            collection.add(documents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
        else:
            collection.add(documents=texts, metadatas=metadatas, ids=ids)
            
        return len(chunks)

    def query_dense(
        self,
        department: str,
        query_text: str,
        top_k: int = 20,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        try:
            collection = self.client.get_collection(name=self._collection_name(department))
        except Exception:
            return []

        if not self.embed_model:
            return []

        query_embedding = self.embed_model.encode([query_text]).tolist()
        
        try:
            kwargs = {
                "query_embeddings": query_embedding,
                "n_results": top_k
            }
            if where_filter:
                kwargs["where"] = where_filter
            results = collection.query(**kwargs)
        except Exception as e:
            logger.warning(f"[CHROMA] Filtered vector query failed ({e}), falling back to basic non-knowledge-graph search.")
            try:
                results = collection.query(
                    query_embeddings=query_embedding,
                    n_results=top_k,
                    where={"source": {"$ne": "knowledge_graph"}}
                )
            except Exception as e2:
                logger.error(f"[CHROMA] Vector query fallback also failed: {e2}")
                return []

        candidates = []
        if results.get('documents') and results['documents'][0]:
            docs = results['documents'][0]
            metas = results['metadatas'][0] if results.get('metadatas') and results['metadatas'][0] else [{}] * len(docs)
            distances = results['distances'][0] if results.get('distances') and results['distances'][0] else [0.0] * len(docs)
            ids = results['ids'][0] if results.get('ids') and results['ids'][0] else [f"doc_{i}" for i in range(len(docs))]
            
            for doc_id, doc, meta, distance in zip(ids, docs, metas, distances):
                candidates.append({
                    "id": doc_id,
                    "text": doc,
                    "metadata": meta,
                    "distance": float(distance)
                })
        return candidates

    def search_exact_text(
        self,
        department: str,
        keyword: str,
        limit: int = 15,
        allowed_roles: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        try:
            collection = self.client.get_collection(name=self._collection_name(department))
        except Exception:
            return []

        try:
            results = collection.get(
                where_document={"$contains": keyword},
                limit=limit
            )
        except Exception as e:
            logger.warning(f"[CHROMA] Exact document search error: {e}")
            return []

        matches = []
        if results and results.get('documents'):
            docs = results['documents']
            metas = results['metadatas'] if results.get('metadatas') else [{}] * len(docs)
            ids = results['ids'] if results.get('ids') else [f"doc_{i}" for i in range(len(docs))]
            
            for doc_id, doc, meta in zip(ids, docs, metas):
                if allowed_roles:
                    doc_min_role = meta.get("min_role", "employee")
                    if doc_min_role not in allowed_roles:
                        continue
                matches.append({
                    "id": doc_id,
                    "text": doc,
                    "metadata": meta,
                    "distance": 0.0
                })
        return matches

    def delete_by_source(self, department: str, source_path: str) -> None:
        try:
            collection = self.client.get_collection(name=self._collection_name(department))
            collection.delete(where={"source": source_path})
        except Exception as e:
            logger.warning(f"[CHROMA] Delete by source warning: {e}")

    def delete_department(self, department: str) -> None:
        try:
            self.client.delete_collection(name=self._collection_name(department))
        except Exception as e:
            logger.warning(f"[CHROMA] Delete collection warning: {e}")
