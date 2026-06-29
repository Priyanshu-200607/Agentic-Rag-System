from ollama import chat

class DepartmentAgent:
    def __init__(self, department_name, client, embed_model, llm_model_name, kg=None):
        self.department_name = department_name
        self.client = client
        self.embed_model = embed_model
        self.llm_model_name = llm_model_name
        self.collection_name = f"dept_{department_name}" if len(department_name) < 3 else department_name
        self.kg = kg

    def query(self, query_text, n_results=3, distance_threshold=1.2):
        try:
            collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            return "No documents found for this department."

        query_embedding = self.embed_model.encode([query_text]).tolist()
        results = collection.query(query_embeddings=query_embedding, n_results=n_results)

        valid_chunks = []
        if results['distances'] and results['distances'][0]:
            for i, dist in enumerate(results['distances'][0]):
                if dist < distance_threshold:
                    valid_chunks.append(results['documents'][0][i])

        # --- GRAPH RAG: Get Knowledge Graph Facts ---
        kg_facts = []
        if self.kg:
            kg_facts = self.kg.get_context_for_entities(query_text, self.llm_model_name)
            
        kg_context = "\n".join(kg_facts) if kg_facts else ""
        
        combined_context = ""
        if valid_chunks:
            combined_context += "--- VECTOR DB CONTEXT ---\n" + "\n\n".join(valid_chunks) + "\n\n"
        if kg_context:
            combined_context += "--- KNOWLEDGE GRAPH FACTS ---\n" + kg_context + "\n\n"
            
        if not combined_context:
            return "I don't know. (No relevant information found)"

        prompt = f"""
        Answer ONLY from the context provided below (which includes Vector DB text and structured Knowledge Graph facts).
        If the answer cannot be found in the context, reply exactly with: I don't know.
        You are a strict data parser. DO NOT use external knowledge.

        Context:
        {combined_context}

        Question:
        {query_text}

        Answer:
        """
        response = chat(
            model=self.llm_model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.message.content
