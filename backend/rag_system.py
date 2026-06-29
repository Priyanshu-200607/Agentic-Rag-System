import json
from sentence_transformers import SentenceTransformer
import chromadb
from ollama import chat

from document_processor import process_file
from department_agent import DepartmentAgent
from kg_system import KnowledgeGraph

class MultiDeptRAG:
    """Master Agent / Orchestrator for Multi-Department RAG"""
    def __init__(self, db_path="./chroma_db_multi", embed_model_name="BAAI/bge-small-en-v1.5", llm_model_name="gemma2:2b"):
        print("Initializing Agentic Orchestrator System...")
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
        safe_name = f"dept_{department_name}" if len(department_name) < 3 else department_name
        collection = self.client.get_or_create_collection(name=safe_name)
        
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
            embeddings = self.embed_model.encode(documents, show_progress_bar=True).tolist()
            start_id = collection.count()
            ids = [str(start_id + i) for i in range(len(documents))]
            
            batch_size = 5000
            for i in range(0, len(documents), batch_size):
                collection.add(
                    ids=ids[i:i+batch_size],
                    documents=documents[i:i+batch_size],
                    embeddings=embeddings[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size]
                )
            
            print(f"Extracting Knowledge Graph facts from {len(documents)} chunks...")
            # Limiting to first 100 chunks for performance, can be expanded to background workers later
            for doc in documents[:100]:
                self.kg.extract_from_text(doc, self.llm_model_name)
            print("Knowledge Graph extraction complete!")

    def admin_delete_file(self, department_name, file_path):
        safe_name = f"dept_{department_name}" if len(department_name) < 3 else department_name
        try:
            self.client.get_collection(name=safe_name).delete(where={"source": file_path})
        except Exception:
            pass

    def route_query(self, query, allowed_departments):
        prompt = f"""
        You are a routing assistant. Decide which departments should be queried based on the query.
        Available departments: {', '.join(allowed_departments)}

        Query: {query}

        Return ONLY a valid JSON list of department names.
        """
        response = chat(
            model=self.llm_model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            content = response.message.content
            start, end = content.find("["), content.find("]") + 1
            if start != -1 and end != -1:
                return [d for d in json.loads(content[start:end]) if d in allowed_departments]
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

        agent_responses = {
            dept: self.get_agent(dept).query(query) 
            for dept in active_target_departments
        }

        synthesis_prompt = f"""
        You are a Master Agent. Synthesize a unified, coherent response to the user's query based on the department agents' answers.
        If all agents say they don't know, just tell the user you don't have the information. Do not mention agents in the final response.
        You are strictly forbidden from answering the user's query using your own knowledge. You must ONLY formulate an answer using the provided Responses. If the responses contain 'I don't know', you must also say 'I don't know'.

        User Query: {query}

        Responses:
        """
        for dept, resp in agent_responses.items():
            synthesis_prompt += f"\n- {dept.upper()}: {resp}"

        synthesis_prompt += "\n\nSynthesized Final Answer:"

        final_response = chat(
            model=self.llm_model_name,
            messages=[{"role": "user", "content": synthesis_prompt}]
        )
        return final_response.message.content
