import json
import uuid
import time
import threading
from sentence_transformers import SentenceTransformer
import chromadb
from ollama import chat

from document_processor import process_file
from department_agent import DepartmentAgent
from kg_system import KnowledgeGraph

# Fix #7: Cap history at this many entries before pruning oldest
HISTORY_MAX_ENTRIES = 500

# Fix #3: Max concurrent KG extraction threads (prevents Ollama RAM saturation)
_kg_semaphore = threading.Semaphore(1)

# Consistent collection naming — single source of truth for all files
def get_collection_name(department_name: str) -> str:
    return f"dept_{department_name}"

class MultiDeptRAG:
    """Master Agent / Orchestrator for Multi-Department RAG"""
    def __init__(self, db_path="./chroma_db_multi", embed_model_name="BAAI/bge-small-en-v1.5", llm_model_name="gemma2:2b"):
        print("Initializing Agentic Orchestrator System...")
        # GPU encoding is fast for batch uploads. The 140MB idle VRAM cost is trivial
        # on an RTX 4060 (8GB). The idle GPU activity you saw before was from the
        # unthrottled KG extraction thread — that's now fixed with a semaphore + rate limit.
        self.embed_model = SentenceTransformer(embed_model_name)
        self.client = chromadb.PersistentClient(path=db_path)
        self.llm_model_name = llm_model_name
        self.agents = {}
        self.kg = KnowledgeGraph()
        print("Master Agent and Department Agents ready.")

    def get_agent(self, department_name):
        if department_name not in self.agents:
            self.agents[department_name] = DepartmentAgent(
                department_name, self.client, self.embed_model, self.llm_model_name, self.kg
            )
        return self.agents[department_name]

    def admin_upload_to_department(self, department_name, file_paths, chunk_size=500, overlap=100):
        collection_name = get_collection_name(department_name)
        collection = self.client.get_or_create_collection(name=collection_name)

        documents = []
        metadatas = []
        step = chunk_size - overlap

        for path in file_paths:
            path = path.strip()
            text = process_file(path)
            if not text:
                continue
            for i in range(0, len(text), step):
                chunk = text[i:i + chunk_size]
                if chunk.strip():
                    documents.append(chunk)
                    metadatas.append({"source": path, "department": department_name})

        if documents:
            # Encode embeddings on CPU — no GPU needed, frees VRAM
            embeddings = self.embed_model.encode(documents, show_progress_bar=True).tolist()
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]

            batch_size = 5000
            for i in range(0, len(documents), batch_size):
                collection.add(
                    ids=ids[i:i+batch_size],
                    documents=documents[i:i+batch_size],
                    embeddings=embeddings[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size]
                )

            print(f"Vectors stored. Scheduling KG extraction for {len(documents)} chunks...")

            # Fix #3: Background thread with semaphore (max 1 concurrent KG job)
            # and rate-limiting sleep to prevent Ollama/CPU saturation.
            # We pass a COPY of documents to avoid holding the upload request's memory.
            docs_copy = list(documents)

            def run_kg_extraction(docs, dept):
                # Process the chunks in massive parallel batches on the GPU
                batch_size = 32
                with _kg_semaphore:
                    print(f"\n[BACKGROUND TASK] KG extraction started for {dept} ({len(docs)} chunks)...")
                    print(f"-> Extracting knowledge graph facts in batches of {batch_size}...")
                    
                    for i in range(0, len(docs), batch_size):
                        batch = docs[i:i + batch_size]
                        self.kg.extract_from_texts(batch, dept)
                        
                        if (i + len(batch)) % (batch_size * 5) == 0 or (i + len(batch)) == len(docs):
                            print(f"[BACKGROUND TASK] KG extraction progress: {i + len(batch)}/{len(docs)} chunks done")
                    
                    self.kg.invalidate_cache()
                    print(f"[BACKGROUND TASK] KG extraction complete for {dept}!\n")

            thread = threading.Thread(
                target=run_kg_extraction,
                args=(docs_copy, department_name),
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
            print(f"Cleared ChromaDB collection: {collection_name}")
        except Exception as e:
            print(f"ChromaDB clear warning: {e}")

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
        print(f"Cleared KG edges for department: {department_name}")

        # 3. Remove the lazy-loaded agent so it is recreated fresh on next query
        if department_name in self.agents:
            del self.agents[department_name]

    def route_query(self, query, allowed_departments):
        # Fix #4: Truncate query to prevent LLM context overflow in router
        query_truncated = query[:1000]
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

    def process_request(self, query, username):
        from auth import load_db
        db = load_db()

        if username not in db["users"]:
            return "Access Denied: User not found."

        user = db["users"][username]
        if user.get("status") == "suspended":
            return "Access Denied: Your account is suspended."

        allowed_departments = user.get("allowed_departments", [])
        if not allowed_departments:
            return "Access Denied: You do not have permission for any departments."

        target_departments = self.route_query(query, allowed_departments)

        active_target_departments = [
            dept for dept in target_departments
            if dept in db.get("departments", {}) and db["departments"][dept].get("status", "active") == "active"
        ]

        if not active_target_departments:
            return "Query blocked: The requested departments are currently suspended or offline."

        # Collect responses
        successful_responses = {}
        failed_departments = []
        
        for dept in active_target_departments:
            resp = self.get_agent(dept).query(query)
            if "I don't know" in resp or "No relevant information found" in resp or "No documents found" in resp:
                failed_departments.append(dept)
            else:
                successful_responses[dept] = resp

        if not successful_responses:
            failed_str = ", ".join(failed_departments)
            return f"I don't know. (Debug: Subqueries failed for departments: {failed_str})"

        synthesis_prompt = f"""
        You are a Master Agent. Synthesize a unified, coherent response to the user's query based ONLY on the department agents' answers below.

        Important Rules:
        1. You must ONLY formulate an answer using the provided Responses. Do not use external knowledge.
        2. Combine the information into a single clear answer.
        3. Do NOT mention that a department did not have information.

        User Query: {query[:2000]}

        Responses:
        """
        for dept, resp in successful_responses.items():
            synthesis_prompt += f"\n- {dept.upper()}: {resp}"

        synthesis_prompt += "\n\nSynthesized Final Answer:"

        final_response = chat(
            model=self.llm_model_name,
            messages=[{"role": "user", "content": synthesis_prompt}],
            options={"temperature": 0.0}
        )
        
        final_text = final_response.message.content
        if failed_departments:
            final_text += f"\n\nNote: The {', '.join(failed_departments)} department(s) did not have any relevant information for this query."
            
        return final_text
