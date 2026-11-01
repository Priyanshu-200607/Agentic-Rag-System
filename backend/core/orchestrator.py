"""
Master Agent & Orchestrator (Core Domain Logic).
Coordinates multi-department RAG query routing, query condensation, System 1 triage,
and ingestion/deletion pipelines through abstract provider ports.
"""

import os
import json
import uuid
import time
import threading
import logging
from typing import Dict, Any, List, Optional, Generator

import config
from core.decision_engine import LocalDecisionEngine
from core.department_agent import DepartmentAgent
from core.document_processor import process_file, determine_document_access_level
from core.chunking import create_parent_child_chunks
from infrastructure.vector.base import VectorProvider
from infrastructure.graph.base import GraphProvider
from infrastructure.state.base import StateProvider
from infrastructure.storage.base import StorageProvider
from infrastructure.inference.base import InferenceProvider

logger = logging.getLogger("rag_system")

# Max concurrent KG extraction semaphore
_kg_semaphore = threading.Semaphore(1)
background_tasks = {}

def get_collection_name(department_name: str) -> str:
    return f"dept_{department_name}"

class MultiDeptRAG:
    """Master Agent / Orchestrator for Multi-Department RAG."""

    def __init__(
        self,
        db_path: str = None,
        embed_model_name: str = None,
        llm_model_name: str = None,
        vector_provider: Optional[VectorProvider] = None,
        graph_provider: Optional[GraphProvider] = None,
        state_provider: Optional[StateProvider] = None,
        storage_provider: Optional[StorageProvider] = None,
        inference_provider: Optional[InferenceProvider] = None,
        decision_engine: Optional[LocalDecisionEngine] = None
    ):
        logger.info("[SYSTEM] Initializing Hexagonal Orchestrator System...")
        self.llm_model_name = llm_model_name or getattr(config, "LLM_MODEL_NAME", "llama3")
        self.db_path = db_path or getattr(config, "CHROMA_DB_PATH", "")
        self.embed_model_name = embed_model_name or getattr(config, "EMBED_MODEL_NAME", "BAAI/bge-small-en-v1.5")

        # 1. Decision Engine
        if decision_engine is not None:
            self.decision_engine = decision_engine
        else:
            self.decision_engine = LocalDecisionEngine()

        # 2. Vector Provider
        if vector_provider is not None:
            self.vector_provider = vector_provider
        else:
            from infrastructure.vector.chroma_provider import ChromaVectorProvider
            self.vector_provider = ChromaVectorProvider(db_path=self.db_path, embed_model_name=self.embed_model_name)
        # Expose legacy client attribute
        self.client = getattr(self.vector_provider, "client", None)
        self.embed_model = getattr(self.vector_provider, "embed_model", None)

        # 3. Graph Provider
        if graph_provider is not None:
            self.graph_provider = graph_provider
        else:
            from infrastructure.graph.sqlite_graph_provider import SQLiteGraphProvider
            self.graph_provider = SQLiteGraphProvider()
        # Expose legacy kg attribute
        self.kg = getattr(self.graph_provider, "kg", None)

        # 4. State Provider
        if state_provider is not None:
            self.state_provider = state_provider
        else:
            from infrastructure.state.sqlite_state import SQLiteStateProvider
            self.state_provider = SQLiteStateProvider()

        # 5. Storage Provider
        if storage_provider is not None:
            self.storage_provider = storage_provider
        else:
            from infrastructure.storage.local_storage import LocalDiskStorageProvider
            self.storage_provider = LocalDiskStorageProvider()

        # 6. Inference Provider
        if inference_provider is not None:
            self.inference_provider = inference_provider
        else:
            from infrastructure.inference.ollama_provider import OllamaInferenceProvider
            self.inference_provider = OllamaInferenceProvider(default_model=self.llm_model_name)

        self.agents: Dict[str, DepartmentAgent] = {}
        logger.info("[SYSTEM] Master Agent, System 1 Decision Engine, and Department Agents ready.")

    def get_agent(self, department_name: str) -> DepartmentAgent:
        return self.agents.setdefault(
            department_name,
            DepartmentAgent(
                department_name=department_name,
                vector_provider=self.vector_provider,
                graph_provider=self.graph_provider,
                inference_provider=self.inference_provider,
                decision_engine=self.decision_engine
            )
        )

    def admin_upload_to_department(self, department_name: str, file_paths: List[str], chunk_size: int = None, overlap: int = None):
        all_hierarchical_chunks = []
        raw_documents_for_kg = []
        raw_metadatas_for_kg = []

        for fpath in file_paths:
            extracted_text = process_file(fpath)
            if not extracted_text.strip():
                logger.warning(f"[UPLOAD] Extracted text empty for {fpath}")
                continue

            confidentiality, min_role = determine_document_access_level(fpath)
            chunks = create_parent_child_chunks(
                text=extracted_text,
                source_file=fpath,
                department=department_name,
                parent_size=chunk_size or 1200,
                parent_overlap=overlap or 200,
                child_size=300,
                child_overlap=50,
                min_role=min_role,
                confidentiality=confidentiality
            )
            all_hierarchical_chunks.extend(chunks)
            raw_documents_for_kg.append(extracted_text)
            raw_metadatas_for_kg.append({"source": fpath, "department": department_name})

        # Insert chunks via VectorProvider
        if all_hierarchical_chunks:
            self.vector_provider.insert_chunks(department_name, all_hierarchical_chunks)
            logger.info(f"[UPLOAD] Successfully indexed {len(all_hierarchical_chunks)} chunks into {department_name}")

        # Trigger background Knowledge Graph extraction thread
        if raw_documents_for_kg and self.kg:
            docs_copy = list(raw_documents_for_kg)
            metas_copy = list(raw_metadatas_for_kg)
            thread = threading.Thread(
                target=self._run_kg_extraction_background,
                args=(docs_copy, metas_copy, department_name),
                daemon=True
            )
            thread.start()

    def _run_kg_extraction_background(self, docs: list, metadatas: list, department: str):
        with _kg_semaphore:
            task_id = str(uuid.uuid4())
            background_tasks[task_id] = {"status": "running", "department": department, "start_time": time.time()}
            try:
                for text, meta in zip(docs, metadatas):
                    source = meta.get("source", "unknown")
                    self.kg.build_from_text(
                        text,
                        llm_model_name=self.llm_model_name,
                        source_file=source,
                        department=department
                    )
                background_tasks[task_id]["status"] = "completed"
            except Exception as e:
                logger.error(f"[KG TASK] Background extraction error: {e}")
                background_tasks[task_id]["status"] = "failed"
                background_tasks[task_id]["error"] = str(e)

    def admin_delete_file(self, department_name: str, file_path: str):
        self.vector_provider.delete_by_source(department_name, file_path)
        if self.graph_provider:
            self.graph_provider.admin_delete_file(file_path)

    def admin_clear_department(self, department_name: str):
        self.vector_provider.delete_department(department_name)
        if self.graph_provider:
            self.graph_provider.delete_department(department_name)
        if department_name in self.agents:
            del self.agents[department_name]

    def route_query(self, query: str, allowed_departments: list, user_role: str = "user") -> list:
        query_truncated = query[:getattr(config, "MAX_QUERY_CHARS", 2000)]
        triage = self.decision_engine.triage_request(
            query_truncated,
            user_role=user_role,
            allowed_departments=allowed_departments
        )
        target_depts = triage.get("target_departments", allowed_departments)
        valid = [d for d in target_depts if d in allowed_departments]
        return valid if valid else allowed_departments

    def evaluate_response(self, query: str, draft_answer: str) -> dict:
        result = self.decision_engine.evaluate_answer(query, draft_answer)
        logger.info(f"[QUERY] System 1 Evaluator gave score {result['score']}/10: {result.get('feedback', '')}")
        return result

    def process_request(self, query: str, username: str, chat_history: list = None) -> Generator[str, None, None]:
        logger.info(f"[QUERY] User {username} asked: {query}")
        effective_query = query
        if chat_history and hasattr(self.decision_engine, "condense_conversational_query"):
            effective_query = self.decision_engine.condense_conversational_query(query, chat_history)

        user = self.state_provider.get_user(username)
        if not user:
            yield json.dumps({"type": "answer", "message": "User not found."}) + "\n"
            return

        if user.status == "suspended":
            yield json.dumps({"type": "answer", "message": "Your account is suspended."}) + "\n"
            return

        user_role = user.role
        allowed_departments = user.allowed_departments
        if not allowed_departments:
            yield json.dumps({"type": "answer", "message": "You do not have access to any departments."}) + "\n"
            return

        yield json.dumps({"type": "status", "message": "Routing query..."}) + "\n"
        target_departments = self.route_query(effective_query, allowed_departments, user_role=user_role)

        all_depts = self.state_provider.list_departments()
        active_target_departments = [
            dept for dept in target_departments
            if dept in all_depts and all_depts[dept].get("status", "active") == "active"
        ]

        if not active_target_departments:
            yield json.dumps({"type": "answer", "message": "The required department is currently inactive."}) + "\n"
            return

        yield json.dumps({"type": "status", "message": f"Querying {', '.join(active_target_departments)}..."}) + "\n"

        dept_answers = {}
        for dept in active_target_departments:
            agent = self.get_agent(dept)
            ans = agent.query(effective_query, user_role=user_role)
            dept_answers[dept] = ans

        if len(dept_answers) == 1:
            dept = list(dept_answers.keys())[0]
            final_answer = dept_answers[dept]
        else:
            yield json.dumps({"type": "status", "message": "Synthesizing cross-department findings..."}) + "\n"
            combined_context = "\n\n".join([f"--- Department {dept} Findings ---\n{ans}" for dept, ans in dept_answers.items()])
            synth_prompt = f"""You are the Master Agent. Combine the findings from the multiple departments into a unified, clear, non-repetitive response:
{combined_context}
Question: {effective_query}
"""
            final_answer = self.inference_provider.chat(
                [{"role": "user", "content": synth_prompt}],
                model=self.llm_model_name,
                temperature=0.0
            )

        yield json.dumps({"type": "answer", "message": final_answer}) + "\n"
