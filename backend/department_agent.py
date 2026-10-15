import json
import re
from ollama import chat
import config
from resource_manager import ResourceManager

class DepartmentAgent:
    def __init__(self, department_name, client, embed_model, llm_model_name, kg=None, decision_engine=None):
        self.department_name = department_name
        self.client = client
        self.embed_model = embed_model
        self.llm_model_name = llm_model_name
        self.collection_name = f"dept_{department_name}"
        self.kg = kg
        self.decision_engine = decision_engine

    def search_vector_db(self, query_text, distance_threshold=1.5):
        try:
            collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            return "No documents found."
        
        query_embedding = self.embed_model.encode([query_text]).tolist()
        results = collection.query(
            query_embeddings=query_embedding, 
            n_results=5,
            where={"source": {"$ne": "knowledge_graph"}}
        )
        
        chunks = []
        if results.get('documents') and results['documents'][0]:
            docs = results['documents'][0]
            metas = results['metadatas'][0] if results.get('metadatas') and results['metadatas'][0] else [{}] * len(docs)
            distances = results['distances'][0] if results.get('distances') and results['distances'][0] else [0] * len(docs)
            
            for doc, meta, distance in zip(docs, metas, distances):
                if distance <= distance_threshold:
                    source = meta.get('source', 'Unknown')
                    chunks.append(f"[Source: {source}]\n{doc}")
                
        return "\n\n".join(chunks) if chunks else "No documents found."

    def search_knowledge_graph(self, entity):
        if not self.kg:
            return "Knowledge graph not available."
        facts = self.kg.get_context_for_entities(entity, self.llm_model_name, self.department_name, max_hops=2, max_facts=30)
        if not facts:
            # Fallback to direct SQL LIKE search for exact keyword matching (solves log IDs and exact metrics)
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


    def search_exact_text(self, keyword):
        try:
            collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            return "No documents found."
            
        results = collection.get(
            where_document={"$contains": keyword},
            limit=15
        )
        
        chunks = []
        if results and results.get('documents'):
            docs = results['documents']
            metas = results['metadatas'] if results.get('metadatas') else [{}] * len(docs)
            for doc, meta in zip(docs, metas):
                source = meta.get('source', 'Unknown')
                chunks.append(f"[Source: {source}]\n{doc}")
                
        return "\n\n".join(chunks) if chunks else "No exact matches found."

    def query(self, query_text, distance_threshold=1.5):
        query_text_safe = query_text[:config.MAX_QUERY_CHARS]
        
        # --- PHASE 3: SUB-SECOND ROUTING WITH LOCAL DECISION ENGINE (LAYA / SYSTEM 1) ---
        if self.decision_engine:
            triage = self.decision_engine.triage_request(
                query_text_safe,
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

        # Step 3.3: Parallel Speculative Execution
        observation = ""
        import concurrent.futures
        
        if confidence < 0.85:
            # Ambiguous query: Fire both in parallel! Pass full query to vector DB (Fix Bug B4)
            print(f"[{self.department_name} Agent] Low routing confidence ({confidence}). Firing parallel hybrid search.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_vec = executor.submit(self.search_vector_db, query_text_safe, distance_threshold)
                future_kg = executor.submit(self.search_knowledge_graph, entity)
                
                obs_vec = future_vec.result()
                obs_kg = future_kg.result()
                
                observation = f"--- Vector DB Results ---\n{obs_vec}\n\n--- Knowledge Graph Results ---\n{obs_kg}"
        else:
            # High confidence: Direct routing
            print(f"[{self.department_name} Agent] High routing confidence ({confidence}). Routing to {target}.")
            if target == "knowledge_graph":
                observation = self.search_knowledge_graph(entity)
            elif target == "exact_text":
                exact_id = re.search(r'\b(user_\d+|req-\d+|id-\d+|log_\d+)\b', query_text_safe, re.IGNORECASE)
                keyword = exact_id.group(0) if exact_id else entity
                observation = self.search_exact_text(keyword)
            else:
                observation = self.search_vector_db(query_text_safe, distance_threshold)

        # Step 3.4: The Synthesizer (Single LLM Call)
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

        response = chat(
            model=self.llm_model_name,
            messages=messages,
            options={"temperature": 0.0}
        )
        
        return response.message.content.strip()
