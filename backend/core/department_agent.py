"""
Department Agent Coordinator (Core Domain Logic).
Coordinates hybrid retrieval, cross-encoder reranking, and synthesis for a specific business unit.
Decoupled from physical databases via VectorProvider, GraphProvider, and InferenceProvider ports.
"""

import sys
import re
import concurrent.futures
from typing import Optional, List, Dict, Any
from core.reranker import LocalReranker
from core.hybrid_retriever import BM25Index, reciprocal_rank_fusion
from infrastructure.vector.base import VectorProvider
from infrastructure.graph.base import GraphProvider
from infrastructure.inference.base import InferenceProvider
import config

try:
    from ollama import chat
except ImportError:
    chat = None

class DepartmentAgent:
    """
    Department-level analytical agent.
    Combines dense vectors, BM25 exact keywords, knowledge graph traversals, and cross-encoder rescoring.
    """
    def __init__(
        self,
        department_name: str,
        client = None,
        embed_model = None,
        llm_model_name: str = None,
        kg = None,
        decision_engine = None,
        vector_provider: Optional[VectorProvider] = None,
        graph_provider: Optional[GraphProvider] = None,
        inference_provider: Optional[InferenceProvider] = None
    ):
        self.department_name = department_name
        self.client = client
        self.embed_model = embed_model
        self.llm_model_name = llm_model_name or getattr(config, "LLM_MODEL_NAME", "llama3")
        self.collection_name = f"dept_{department_name}"
        self.kg = kg
        self.decision_engine = decision_engine
        self.reranker = LocalReranker()

        # Bind VectorProvider (or create adapter from client)
        if vector_provider is not None:
            self.vector_provider = vector_provider
        elif client is not None:
            from infrastructure.vector.chroma_provider import ChromaVectorProvider
            self.vector_provider = ChromaVectorProvider(embed_model=embed_model)
            self.vector_provider.client = client
        else:
            from infrastructure.vector.chroma_provider import ChromaVectorProvider
            self.vector_provider = ChromaVectorProvider(embed_model=embed_model)
            self.client = self.vector_provider.client
            self.embed_model = self.vector_provider.embed_model

        # Bind GraphProvider (or create adapter from kg)
        if graph_provider is not None:
            self.graph_provider = graph_provider
        elif kg is not None:
            from infrastructure.graph.sqlite_graph_provider import SQLiteGraphProvider
            self.graph_provider = SQLiteGraphProvider(kg_instance=kg)
        else:
            from infrastructure.graph.sqlite_graph_provider import SQLiteGraphProvider
            self.graph_provider = SQLiteGraphProvider()
            self.kg = self.graph_provider.kg

        # Bind InferenceProvider
        if inference_provider is not None:
            self.inference_provider = inference_provider
        else:
            from infrastructure.inference.ollama_provider import OllamaInferenceProvider
            self.inference_provider = OllamaInferenceProvider(default_model=self.llm_model_name)

    def search_vector_db(self, query_text: str, distance_threshold: float = 1.5, user_role: str = "employee") -> str:
        try:
            collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            return "No documents found."

        # Role clearance hierarchy for Document-Level ABAC
        role_hierarchy = {
            "admin": {"admin", "manager", "employee", "user"},
            "manager": {"manager", "employee", "user"},
            "employee": {"employee", "user"},
            "user": {"employee", "user"}
        }
        allowed_roles = role_hierarchy.get(user_role, {"employee", "user"})

        # ChromaDB pre-filtering clause for Document-Level ABAC
        where_clause = {"source": {"$ne": "knowledge_graph"}}
        if user_role not in ("admin", "manager"):
            where_clause = {
                "$and": [
                    {"source": {"$ne": "knowledge_graph"}},
                    {"min_role": {"$ne": "admin"}},
                    {"min_role": {"$ne": "manager"}}
                ]
            }
        elif user_role == "manager":
            where_clause = {
                "$and": [
                    {"source": {"$ne": "knowledge_graph"}},
                    {"min_role": {"$ne": "admin"}}
                ]
            }

        candidate_docs = []
        try:
            query_embedding = self.embed_model.encode([query_text]).tolist()
            try:
                results = collection.query(
                    query_embeddings=query_embedding,
                    n_results=20,
                    where=where_clause
                )
            except Exception:
                results = collection.query(
                    query_embeddings=query_embedding,
                    n_results=20,
                    where={"source": {"$ne": "knowledge_graph"}}
                )

            if results.get('documents') and results['documents'][0]:
                docs = results['documents'][0]
                metas = results['metadatas'][0] if results.get('metadatas') and results['metadatas'][0] else [{}] * len(docs)
                distances = results['distances'][0] if results.get('distances') and results['distances'][0] else [0] * len(docs)
                ids = results['ids'][0] if results.get('ids') and results['ids'][0] else [f"doc_{i}" for i in range(len(docs))]

                for doc_id, doc, meta, distance in zip(ids, docs, metas, distances):
                    doc_min_role = meta.get("min_role", "employee")
                    if doc_min_role not in allowed_roles:
                        continue

                    if distance <= distance_threshold:
                        candidate_docs.append({
                            "id": doc_id,
                            "text": doc,
                            "metadata": meta,
                            "distance": distance
                        })
        except Exception:
            pass

        if not candidate_docs:
            return "No documents found."

        # 2. Hybrid Lexical Search (BM25) & Reciprocal Rank Fusion (RRF)
        try:
            bm25 = BM25Index()
            bm25.fit(candidate_docs)
            lexical_candidates = bm25.search(query_text, top_n=20)
            fused_candidates = reciprocal_rank_fusion(candidate_docs, lexical_candidates, k=60)
        except Exception:
            fused_candidates = candidate_docs

        # 3. Cross-Encoder Reranking
        top_reranked = self.reranker.rerank(query_text, fused_candidates, top_n=5)

        # 4. Context Assembly with Parent-Child De-duplication
        chunks = []
        seen_parents = set()
        
        for cand in top_reranked:
            meta = cand.get("metadata", {})
            source = meta.get("source", "Unknown")
            parent_id = meta.get("parent_id")
            parent_text = meta.get("parent_text")
            
            if parent_id and parent_text:
                if parent_id in seen_parents:
                    continue
                seen_parents.add(parent_id)
                chunks.append(f"[Source: {source}]\n{parent_text}")
            else:
                chunks.append(f"[Source: {source}]\n{cand.get('text', '')}")
                
        return "\n\n".join(chunks) if chunks else "No documents found."

    def search_knowledge_graph(self, entity: str) -> str:
        if not self.kg:
            return "Knowledge graph not available."
        facts = self.kg.get_context_for_entities(
            entity,
            self.llm_model_name,
            self.department_name,
            max_hops=2,
            max_facts=30
        )
        if not facts:
            try:
                cursor = self.kg.conn.cursor()
                cursor.execute(
                    "SELECT source, relation, target FROM edges WHERE department = ? AND (source LIKE ? OR target LIKE ? OR relation LIKE ?) LIMIT 30",
                    (self.department_name, f"%{entity}%", f"%{entity}%", f"%{entity}%")
                )
                rows = cursor.fetchall()
                facts = [f"{row[0]} | {row[1]} | {row[2]}" for row in rows]
            except Exception:
                pass
        return "\n".join(facts) if facts else "No facts found."

    def search_exact_text(self, keyword: str, user_role: str = "employee") -> str:
        try:
            collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            return "No documents found."

        try:
            results = collection.get(
                where_document={"$contains": keyword},
                limit=15
            )
        except Exception:
            return "No exact matches found."

        role_hierarchy = {
            "admin": {"admin", "manager", "employee", "user"},
            "manager": {"manager", "employee", "user"},
            "employee": {"employee", "user"},
            "user": {"employee", "user"}
        }
        allowed_roles = role_hierarchy.get(user_role, {"employee", "user"})

        chunks = []
        seen_parents = set()
        if results and results.get('documents'):
            docs = results['documents']
            metas = results['metadatas'] if results.get('metadatas') else [{}] * len(docs)
            for doc, meta in zip(docs, metas):
                doc_min_role = meta.get("min_role", "employee")
                if doc_min_role not in allowed_roles:
                    continue
                source = meta.get('source', 'Unknown')
                parent_id = meta.get("parent_id")
                parent_text = meta.get("parent_text")
                if parent_id and parent_text:
                    if parent_id in seen_parents:
                        continue
                    seen_parents.add(parent_id)
                    chunks.append(f"[Source: {source}]\n{parent_text}")
                else:
                    chunks.append(f"[Source: {source}]\n{doc}")

        return "\n\n".join(chunks) if chunks else "No exact matches found."

    def query(self, query_text: str, distance_threshold: float = 1.5, user_role: str = "employee") -> str:
        query_text_safe = query_text[:getattr(config, "MAX_QUERY_CHARS", 2000)]
        
        if self.decision_engine:
            triage = self.decision_engine.triage_request(
                query_text_safe,
                user_role=user_role,
                allowed_departments=[self.department_name]
            )
            target = triage.get("retrieval_mode", "vector_db")
            confidence = triage.get("confidence", 0.95)
            entity = triage.get("extracted_entity", query_text_safe)
        else:
            target = "vector_db"
            confidence = 0.95
            entity = query_text_safe
            if any(term in query_text_safe.lower() for term in ["relationship", "who is", "reports to", "connected to"]):
                target = "knowledge_graph"

        observation = ""
        if confidence < 0.85:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_vec = executor.submit(self.search_vector_db, query_text_safe, distance_threshold, user_role)
                future_kg = executor.submit(self.search_knowledge_graph, entity)
                obs_vec = future_vec.result()
                obs_kg = future_kg.result()
                observation = f"--- Vector DB Results ---\n{obs_vec}\n\n--- Knowledge Graph Results ---\n{obs_kg}"
        else:
            if target == "knowledge_graph":
                observation = self.search_knowledge_graph(entity)
            elif target == "exact_text":
                exact_id = re.search(r'\b(user_\d+|req-\d+|id-\d+|log_\d+)\b', query_text_safe, re.IGNORECASE)
                keyword = exact_id.group(0) if exact_id else entity
                observation = self.search_exact_text(keyword, user_role=user_role)
            else:
                observation = self.search_vector_db(query_text_safe, distance_threshold, user_role=user_role)

        system_prompt = f"""You are an analytical agent for the {self.department_name} department.
Your task is to answer the user's query based ONLY on the provided retrieved data chunks.
If the data chunks do not contain the answer, state that you do not have enough information.

IMPORTANT RESOLUTION RULE:
If you see conflicting information across chunks, look at the [Source: filename] metadata. 
ALWAYS prioritize files with "current" or newer years (e.g. 2025) over files with "past" or older years.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User Query: {query_text_safe}\n\nRetrieved Data:\n{observation}"}
        ]

        # Check if department_agent.chat was patched in sys.modules
        chat_callable = None
        if "department_agent" in sys.modules:
            chat_callable = getattr(sys.modules["department_agent"], "chat", None)
        if chat_callable is None:
            chat_callable = chat

        if chat_callable is not None:
            response = chat_callable(
                model=self.llm_model_name,
                messages=messages,
                options={"temperature": 0.0}
            )
            if hasattr(response, "message") and hasattr(response.message, "content"):
                return response.message.content.strip()
            return str(response).strip()

        return self.inference_provider.chat(messages, model=self.llm_model_name, temperature=0.0)
