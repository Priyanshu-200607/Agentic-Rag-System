from ollama import chat
import config
from resource_manager import ResourceManager

class DepartmentAgent:
    def __init__(self, department_name, client, embed_model, llm_model_name, kg=None):
        self.department_name = department_name
        self.client = client
        self.embed_model = embed_model
        self.llm_model_name = llm_model_name
        self.collection_name = f"dept_{department_name}"
        self.kg = kg

    def query(self, query_text, distance_threshold=1.5):
        # Fix #4: Truncate query before encoding to prevent embedding model issues
        query_text_safe = query_text[:config.MAX_QUERY_CHARS]
        context_limit = ResourceManager.get_dynamic_context_limit(self.llm_model_name)

        try:
            collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            return "No documents found for this department."

        query_embedding = self.embed_model.encode([query_text_safe]).tolist()
        
        # Phase 3: Dynamic Top-K Retrieval
        # Calculate optimal chunks (assume ~600 chars per chunk)
        # Cap at 50 to prevent massive latency on small chunks
        optimal_n_results = min(50, max(5, context_limit // 600))
        
        results = collection.query(query_embeddings=query_embedding, n_results=optimal_n_results)

        valid_chunks = results['documents'][0] if results.get('documents') and results['documents'][0] else []

        # --- GRAPH RAG: Get Knowledge Graph Facts ---
        kg_facts = []
        if self.kg:
            # Phase 3: Dynamic Multi-Hop Expansion based on context limit
            max_facts = config.MAX_KG_FACTS if context_limit <= 8000 else 100
            max_hops = config.MAX_KG_HOPS if context_limit <= 8000 else 3
            
            kg_facts = self.kg.get_context_for_entities(
                query_text_safe, self.llm_model_name, self.department_name, max_hops=max_hops, max_facts=max_facts
            )

        kg_context = "\n".join(kg_facts) if kg_facts else ""

        combined_context = ""
        if valid_chunks:
            combined_context += "--- VECTOR DB CONTEXT ---\n" + "\n\n".join(valid_chunks) + "\n\n"
        if kg_context:
            combined_context += "--- KNOWLEDGE GRAPH FACTS ---\n" + kg_context + "\n\n"

        if not combined_context:
            return "I don't know. (No relevant information found)"

        # Fix #4: Hard cap combined context to stay within LLM context window.
        # This prevents silent LLM truncation or errors on huge document retrievals.
        if len(combined_context) > context_limit:
            combined_context = combined_context[:context_limit] + "\n[Context truncated to fit model limits]"

        prompt = f"""
        Answer ONLY from the context provided below (which includes Vector DB text and structured Knowledge Graph facts).
        If the answer cannot be found in the context, reply exactly with: I don't know.
        You are a strict data parser. DO NOT use external knowledge.

        Context:
        {combined_context}

        Question:
        {query_text_safe}

        Answer:
        """
        response = chat(
            model=self.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0}
        )
        return response.message.content
