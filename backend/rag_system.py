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

# Fix #3: Max concurrent KG extraction threads (prevents Ollama RAM saturation)
_kg_semaphore = threading.Semaphore(1)

# Background tasks tracking
background_tasks = {}


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

        self.embed_model = SentenceTransformer(self.embed_model_name)
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.agents = {}
        self.kg = KnowledgeGraph()
        logger.info("[SYSTEM] Master Agent and Department Agents ready.")

    def get_agent(self, department_name):
        return self.agents.setdefault(
            department_name,
            DepartmentAgent(department_name, self.client, self.embed_model, self.llm_model_name, self.kg)
        )

    def admin_upload_to_department(self, department_name, file_paths, chunk_size=500, overlap=100):
        collection_name = get_collection_name(department_name)
        collection = self.client.get_or_create_collection(name=collection_name)

        documents = []
        metadatas = []
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)

        for path in tqdm(file_paths, desc="Processing Documents"):
            path = path.strip()
            text = process_file(path)
            if not text:
                continue
            
            chunks = splitter.split_text(text)
            for chunk in chunks:
                if chunk.strip():
                    documents.append(chunk)
                    metadatas.append({"source": path, "department": department_name})

        if documents:
            # Encode embeddings on CPU — no GPU needed, frees VRAM
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
                background_tasks[task_id] = {"task": f"KG Extraction ({dept})", "progress": 0, "total": len(docs), "status": "running"}
                
                with _kg_semaphore:
                    logger.info(f"[TASK] KG extraction started for {dept} ({len(docs)} chunks)...")
                    i = 0
                    pbar = tqdm(total=len(docs), desc=f"KG Extraction ({dept})", unit="chunk")

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
                            facts = [fd["fact"] for fd in facts_data]
                            embeddings = self.embed_model.encode(facts, show_progress_bar=False).tolist()
                            ids = [f"{dept}_kg_{i}_{j}" for j in range(len(facts))]
                            metadatas = [{"source": fd.get("source_file") or "knowledge_graph", "department": dept, "type": "kg_fact"} for fd in facts_data]
                            try:
                                col = self.client.get_collection(name=get_collection_name(dept))
                                col.add(ids=ids, documents=facts, embeddings=embeddings, metadatas=metadatas)
                            except Exception as e:
                                logger.error(f"[SYSTEM] Failed to add KG facts to Chroma: {e}")
                                
                        i += current_batch_size
                        pbar.update(len(batch))
                        background_tasks[task_id]["progress"] = min(i, len(docs))

                    
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
        except Exception:
            pass

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

    def route_query(self, query, allowed_departments):
        # Fix #4: Truncate query to prevent LLM context overflow in router
        query_truncated = query[:config.MAX_QUERY_CHARS]
        prompt = f"""
        You are a routing assistant. Decide which departments should be queried based on the query.
        Available departments: {', '.join(allowed_departments)}

        Query: {query_truncated}

        Return ONLY a valid JSON list of department names from the available list. Use lowercase.
        Example: ["hr", "finance"]
        """
        response = chat(
            model=self.llm_model_name,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            content = response.message.content
            start, end = content.find("["), content.find("]") + 1
            if start != -1 and end != -1:
                return [d.lower() for d in json.loads(content[start:end]) if d.lower() in allowed_departments]
        except Exception:
            pass
        return allowed_departments

    def evaluate_response(self, query, draft_answer):
        prompt = f"""
        You are the Master Reviewer. 
        The user asked: '{query}'
        The Department Agent answered: '{draft_answer}'
        
        Rate how thoroughly this answers the user's original question on a scale of 1 to 10.
        If the score is below 8, provide specific feedback on what is missing or what needs to be searched.
        
        Output EXACTLY in this JSON format:
        {{"score": 8, "feedback": "good"}}
        """
        try:
            response = chat(
                model=self.llm_model_name,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.0}
            )
            content = response.message.content
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                import json
                data = json.loads(match.group(0))
                score = int(data.get("score", 10))
                feedback = data.get("feedback", "")
                logger.info(f"[QUERY] Evaluator gave score {score}/10")
                return {"score": score, "feedback": feedback}
        except Exception as e:
            logger.error(f"[SYSTEM] Evaluation Error: {e}")
        # Default to pass if evaluator fails to avoid breaking
        return {"score": 10, "feedback": ""}

    def process_request(self, query, username):
        logger.info(f"[QUERY] User {username} asked: {query}")
        from auth import load_db
        db = load_db()
        users = db.get("users", {})
        if username not in users:
            yield json.dumps({"type": "answer", "message": "User not found."}) + "\n"
            return

        allowed_departments = users[username].get("allowed_departments", [])
        if not allowed_departments:
            yield json.dumps({"type": "answer", "message": "You do not have access to any departments."}) + "\n"
            return

        yield json.dumps({"type": "status", "message": "Routing query..."}) + "\n"
        target_departments = self.route_query(query, allowed_departments)
        
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
            current_query = query
            best_resp = ""
            success = False
            
            for attempt in range(2): # Max 2 attempts to prevent infinite loop
                resp = agent.query(current_query)
                
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