import json
import uuid
import time
import threading
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb
from ollama import chat

import config
from logger import get_logger
logger = get_logger()
from resource_manager import ResourceManager
from document_processor import process_file
from department_agent import DepartmentAgent
from kg_system import KnowledgeGraph
from decision_engine import LocalDecisionEngine

# Fix #3: Max concurrent KG extraction threads (prevents Ollama RAM saturation)
_kg_semaphore = threading.Semaphore(1)

# Background tasks tracking
background_tasks = {}


def determine_document_access_level(file_path: str, explicit_confidentiality: str = None) -> tuple:
    """
    Returns (confidentiality, min_role) for Document-Level ABAC.
    Categories:
      - 'restricted'   -> min_role 'admin'   (master credentials, executive compensation)
      - 'confidential' -> min_role 'manager' (salaries, performance reviews, termination, nda)
      - 'internal'     -> min_role 'employee' (general departmental procedures, guidelines)
    """
    if explicit_confidentiality in ("restricted", "confidential", "internal", "public"):
        conf = explicit_confidentiality
        min_role = "admin" if conf == "restricted" else ("manager" if conf == "confidential" else "employee")
        return conf, min_role

    import os
    fname = os.path.basename(file_path).lower()
    restricted_keywords = ["master_key", "secret", "private_key", "admin_credential", "executive_comp"]
    confidential_keywords = ["salary", "salaries", "payroll", "compensation", "performance_review", "disciplinary", "termination", "audit_report", "tax_return", "nda"]
    
    if any(k in fname for k in restricted_keywords):
        return "restricted", "admin"
    elif any(k in fname for k in confidential_keywords):
        return "confidential", "manager"
    else:
        return "internal", "employee"

# Consistent collection naming — single source of truth for all files
def get_collection_name(department_name: str) -> str:
    return f"dept_{department_name}"

class MultiDeptRAG:
    """Master Agent / Orchestrator for Multi-Department RAG"""
    def __init__(self, db_path=None, embed_model_name=None, llm_model_name=None):
        logger.info("[SYSTEM] Initializing Agentic Orchestrator System...")
        
        self.db_path = db_path or config.CHROMA_DB_PATH
        self.embed_model_name = embed_model_name or config.EMBED_MODEL_NAME
        self.llm_model_name = llm_model_name or config.LLM_MODEL_NAME

        self.embed_model = SentenceTransformer(self.embed_model_name, device=ResourceManager.get_device())
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.decision_engine = LocalDecisionEngine(device=ResourceManager.get_device())
        self.agents = {}
        self.kg = KnowledgeGraph()
        logger.info("[SYSTEM] Master Agent, System 1 Decision Engine, and Department Agents ready.")

    def get_agent(self, department_name):
        return self.agents.setdefault(
            department_name,
            DepartmentAgent(department_name, self.client, self.embed_model, self.llm_model_name, self.kg, self.decision_engine)
        )

    def admin_upload_to_department(self, department_name, file_paths, chunk_size=None, overlap=None):
        collection_name = get_collection_name(department_name)
        collection = self.client.get_or_create_collection(name=collection_name)

        documents = []
        metadatas = []
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        import os
        
        try:
            from langchain_community.document_loaders.csv_loader import CSVLoader
            from langchain_community.document_loaders import JSONLoader
        except ImportError:
            CSVLoader = None
            JSONLoader = None
            
        chunk_params = ResourceManager.get_optimal_chunk_sizes()
        chunk_size = chunk_size or chunk_params["chunk_size"]
        overlap = overlap or chunk_params["overlap"]

        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)

        for path in tqdm(file_paths, desc="Processing Documents"):
            path = path.strip()
            ext = os.path.splitext(path)[1].lower()
            doc_conf, doc_min_role = determine_document_access_level(path)
            
            # Specialized structured chunking for CSV
            if ext == ".csv" and CSVLoader:
                try:
                    loader = CSVLoader(file_path=path)
                    docs = loader.load()
                    for doc in docs:
                        if doc.page_content.strip():
                            documents.append(doc.page_content)
                            metadatas.append({
                                "source": path,
                                "department": department_name,
                                "confidentiality": doc_conf,
                                "min_role": doc_min_role
                            })
                    continue
                except Exception as e:
                    logger.warning(f"CSVLoader failed for {path}: {e}")
                    
            # Specialized structured chunking for JSON
            if ext == ".json" and JSONLoader:
                try:
                    try:
                        loader = JSONLoader(file_path=path, jq_schema=".[]", text_content=False)
                        docs = loader.load()
                    except Exception:
                        loader = JSONLoader(file_path=path, jq_schema=".", text_content=False)
                        docs = loader.load()
                        
                    for doc in docs:
                        if doc.page_content.strip():
                            documents.append(doc.page_content)
                            metadatas.append({
                                "source": path,
                                "department": department_name,
                                "confidentiality": doc_conf,
                                "min_role": doc_min_role
                            })
                    continue
                except Exception as e:
                    logger.warning(f"JSONLoader failed for {path}: {e}")

            text = process_file(path)
            if not text:
                continue
            
            # Use Parent-Child chunking if available, preserving parent section context
            try:
                from document_processor import create_parent_child_chunks
                pc_chunks = create_parent_child_chunks(text, source_file=path, department=department_name)
                if pc_chunks:
                    for pc in pc_chunks:
                        documents.append(pc["text"])
                        metadatas.append({
                            "source": path,
                            "department": department_name,
                            "parent_id": pc["parent_id"],
                            "parent_text": pc["parent_text"],
                            "confidentiality": doc_conf,
                            "min_role": doc_min_role
                        })
                    continue
            except Exception as e:
                logger.warning(f"Parent-child chunking fallback for {path}: {e}")

            chunks = splitter.split_text(text)
            for chunk in chunks:
                if chunk.strip():
                    documents.append(chunk)
                    metadatas.append({
                        "source": path,
                        "department": department_name,
                        "confidentiality": doc_conf,
                        "min_role": doc_min_role
                    })

        if documents:
            # Encode embeddings on the designated device (GPU if available)
            embeddings = self.embed_model.encode(documents, show_progress_bar=True).tolist()
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]

            batch_size = ResourceManager.get_optimal_batch_sizes()["chroma_batch"]
            for i in tqdm(range(0, len(documents), batch_size), desc="Storing Vectors"):
                collection.add(
                    ids=ids[i:i+batch_size],
                    documents=documents[i:i+batch_size],
                    embeddings=embeddings[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size]
                )

            logger.info(f"[TASK] Vectors stored. Scheduling KG extraction for {len(documents)} chunks...")

            # Fix #3: Background thread with semaphore (max 1 concurrent KG job)
            # and rate-limiting sleep to prevent Ollama/CPU saturation.
            # We pass a COPY of documents to avoid holding the upload request's memory.
            docs_copy = list(documents)
            metadatas_copy = list(metadatas)

            def run_kg_extraction(docs, metas, dept):
                # Process the chunks in massive parallel batches on the GPU
                current_batch_size = ResourceManager.get_optimal_batch_sizes()["kg_batch"]
                task_id = f"kg_{dept}_{uuid.uuid4().hex[:8]}"
                start_time = time.time()
                background_tasks[task_id] = {"task": f"KG Extraction ({dept})", "progress": 0, "total": len(docs), "status": "running", "rate": 0, "start_time": start_time}
                
                import concurrent.futures

                with _kg_semaphore:
                    logger.info(f"[TASK] KG extraction started for {dept} ({len(docs)} chunks)...")
                    i = 0
                    pbar = tqdm(total=len(docs), desc=f"KG Extraction ({dept})", unit="chunk")
                    
                    def store_facts_to_chroma(facts_data, start_idx):
                        if not facts_data: return
                        facts = [fd["fact"] for fd in facts_data]
                        embeddings = self.embed_model.encode(facts, show_progress_bar=False).tolist()
                        ids = [f"{dept}_kg_{start_idx}_{j}" for j in range(len(facts))]
                        metadatas = [{"source": fd.get("source_file") or "knowledge_graph", "department": dept, "type": "kg_fact"} for fd in facts_data]
                        try:
                            col = self.client.get_collection(name=get_collection_name(dept))
                            col.add(ids=ids, documents=facts, embeddings=embeddings, metadatas=metadatas)
                        except Exception as e:
                            logger.error(f"[SYSTEM] Failed to add KG facts to Chroma: {e}")

                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        futures = []
                        while i < len(docs):
                            current_batch_size = ResourceManager.check_memory_pressure(current_batch_size)
                            batch = docs[i:i + current_batch_size]
                            meta_batch = metas[i:i + current_batch_size]
                            source_files = [m["source"] for m in meta_batch]
                            
                            try:
                                facts_data = self.kg.extract_from_texts(batch, dept, source_files)
                            except Exception as e:
                                logger.error(f"[SYSTEM] Aborting KG extraction due to critical error: {e}")
                                background_tasks[task_id]["status"] = "error"
                                background_tasks[task_id]["error"] = str(e)
                                break

                            if facts_data:
                                futures.append(executor.submit(store_facts_to_chroma, facts_data, i))
                                    
                            i += current_batch_size
                            pbar.update(len(batch))
                            progress_val = min(i, len(docs))
                            background_tasks[task_id]["progress"] = progress_val
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                background_tasks[task_id]["rate"] = round(progress_val / elapsed, 1)

                        concurrent.futures.wait(futures)

                    pbar.close()
                    self.kg.invalidate_cache()
                    
                    # Unload REBEL from the GPU to free up VRAM for Ollama
                    import kg_system as kgs
                    if hasattr(kgs, 'unload_rebel'):
                        kgs.unload_rebel()
                        
                    if background_tasks[task_id]["status"] != "error":
                        background_tasks[task_id]["status"] = "completed"
                    logger.info(f"[TASK] KG extraction complete for {dept}!")

            thread = threading.Thread(
                target=run_kg_extraction,
                args=(docs_copy, metadatas_copy, department_name),
                daemon=True
            )
            thread.start()

    def admin_delete_file(self, department_name, file_path):
        collection_name = get_collection_name(department_name)
        try:
            self.client.get_collection(name=collection_name).delete(where={"source": file_path})
        except Exception as e:
            logger.warning(f"[SYSTEM] ChromaDB delete warning: {e}")
            
        try:
            self.kg.admin_delete_file(file_path)
            logger.info(f"[TASK] Cleared KG edges for file: {file_path}")
        except Exception as e:
            logger.warning(f"[SYSTEM] KG DB delete warning: {e}")

    def admin_clear_department(self, department_name):
        """Delete ALL vectors and KG edges for a department in one operation."""
        collection_name = get_collection_name(department_name)

        # 1. Drop the entire ChromaDB collection and recreate it empty
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"[TASK] Cleared ChromaDB collection: {collection_name}")
        except Exception as e:
            logger.warning(f"[SYSTEM] ChromaDB clear warning: {e}")

        # 2. Remove all KG edges for this department from SQLite and rebuild graph
        with self.kg._write_lock:
            self.kg.conn.execute(
                "DELETE FROM edges WHERE department = ?", (department_name,)
            )
            self.kg.conn.commit()
            # Rebuild in-memory graph from remaining edges
            self.kg.load()
        # Invalidate entity cache since graph data changed
        self.kg.invalidate_cache()
        logger.info(f"[TASK] Cleared KG edges for department: {department_name}")

        # 3. Remove the lazy-loaded agent so it is recreated fresh on next query
        if department_name in self.agents:
            del self.agents[department_name]

    def route_query(self, query, allowed_departments, user_role="user"):
        query_truncated = query[:config.MAX_QUERY_CHARS]
        # Fast System 1 classification (<40ms) replacing slow 3s LLM routing
        triage = self.decision_engine.triage_request(
            query_truncated,
            user_role=user_role,
            allowed_departments=allowed_departments
        )
        target_depts = triage.get("target_departments", allowed_departments)
        valid = [d for d in target_depts if d in allowed_departments]
        return valid if valid else allowed_departments

    def evaluate_response(self, query, draft_answer):
        # Fast System 1 answer quality evaluation (<20ms) replacing slow token-by-token LLM scoring
        result = self.decision_engine.evaluate_answer(query, draft_answer)
        logger.info(f"[QUERY] System 1 Evaluator gave score {result['score']}/10: {result.get('feedback', '')}")
        return result

    def process_request(self, query, username, chat_history=None):
        logger.info(f"[QUERY] User {username} asked: {query}")
        
        # Conversational Query Condensation: rewrite follow-up questions using chat context
        effective_query = query
        if chat_history and hasattr(self.decision_engine, "condense_conversational_query"):
            effective_query = self.decision_engine.condense_conversational_query(query, chat_history)

        from auth import load_db
        db = load_db()
        users = db.get("users", {})
        if username not in users:
            yield json.dumps({"type": "answer", "message": "User not found."}) + "\n"
            return

        user_role = users[username].get("role", "user")
        allowed_departments = users[username].get("allowed_departments", [])
        if not allowed_departments:
            yield json.dumps({"type": "answer", "message": "You do not have access to any departments."}) + "\n"
            return

        yield json.dumps({"type": "status", "message": "Routing query..."}) + "\n"
        target_departments = self.route_query(effective_query, allowed_departments, user_role=user_role)
        
        active_target_departments = [
            dept for dept in target_departments
            if dept in db.get("departments", {}) and db["departments"][dept].get("status", "active") == "active"
        ]

        if not active_target_departments:
            yield json.dumps({"type": "answer", "message": "Query blocked: The requested departments are currently suspended or offline."}) + "\n"
            return

        successful_responses = {}
        failed_departments = []
        
        for dept in active_target_departments:
            yield json.dumps({"type": "status", "message": f"Querying department agent: {dept.upper()}..."}) + "\n"
            agent = self.get_agent(dept)
            current_query = effective_query
            best_resp = ""
            success = False
            
            for attempt in range(2): # Max 2 attempts to prevent infinite loop
                resp = agent.query(current_query, user_role=user_role)
                
                if "I don't know" in resp or "No relevant information found" in resp or "No documents found" in resp:
                    if attempt == 1:
                        break # Failed on last attempt
                    # Give it a generic push if it failed completely
                    yield json.dumps({"type": "status", "message": f"{dept.upper()} agent failed. Retrying..."}) + "\n"
                    current_query = f"Original Query: {query}\nFeedback: Your previous search yielded no results. Try searching for different keywords or exact entity names."
                    continue
                
                yield json.dumps({"type": "status", "message": f"Evaluating {dept.upper()} response..."}) + "\n"
                evaluation = self.evaluate_response(query, resp)
                best_resp = resp
                
                if evaluation["score"] >= 8:
                    success = True
                    break
                else:
                    yield json.dumps({"type": "status", "message": f"Refining {dept.upper()} response (Score: {evaluation['score']}/10)..."}) + "\n"
                    current_query = f"Original Query: {query}\nFeedback on previous answer: {evaluation['feedback']}\nPlease use your tools to search again focusing on the feedback."
            
            # Add to successful responses if we have a valid answer
            if best_resp and "I don't know" not in best_resp and "No documents found" not in best_resp:
                successful_responses[dept] = best_resp
            else:
                failed_departments.append(dept)

        if not successful_responses:
            if failed_departments:
                yield json.dumps({"type": "answer", "message": f"I could not find a relevant answer in the following departments: {', '.join(failed_departments)}."}) + "\n"
            else:
                yield json.dumps({"type": "answer", "message": "Based on the available data, I could not find an answer to your question."}) + "\n"
            return
            
        final_answer = ""
        for dept, resp in successful_responses.items():
            final_answer += f"[{dept.upper()}] {resp}\n\n"
            
        yield json.dumps({"type": "answer", "message": final_answer.strip()}) + "\n"