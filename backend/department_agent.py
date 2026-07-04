import json
import re
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

    def search_vector_db(self, query_text):
        try:
            collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            return "No documents found."
        
        query_embedding = self.embed_model.encode([query_text]).tolist()
        results = collection.query(query_embeddings=query_embedding, n_results=15)
        valid_chunks = results['documents'][0] if results.get('documents') and results['documents'][0] else []
        return "\n".join(valid_chunks)

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
        valid_chunks = results['documents'] if results and results.get('documents') else []
        return "\n".join(valid_chunks) if valid_chunks else "No exact matches found."

    def query(self, query_text, distance_threshold=1.5):
        query_text_safe = query_text[:config.MAX_QUERY_CHARS]
        
        system_prompt = f"""You are an analytical agent for the {self.department_name} department.
You MUST use the available tools to find information before answering.
Available tools:
1. search_vector_db(query): Good for semantic searches, policies, general text.
2. search_knowledge_graph(entity): Good for exploring entity relationships.
3. search_exact_text(keyword): Good for EXACT substring matches like log IDs ('sync_salesforce_45'), exact dates, or specific acronyms ('CAC'). Use this if vector search fails to find a specific ID.

To use a tool, output exactly in this format:
Action: tool_name
Action Input: input_string

Then I will provide the Observation.
Once you have the answer, output:
Final Answer: your detailed answer based ONLY on the observations.

User Query: {query_text_safe}
"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        max_steps = 4
        for step in range(max_steps):
            response = chat(
                model=self.llm_model_name,
                messages=messages,
                options={"temperature": 0.0}
            )
            content = response.message.content
            messages.append({"role": "assistant", "content": content})
            
            if "Final Answer:" in content:
                # Extract just the final answer part
                return content.split("Final Answer:")[-1].strip()
                
            action_match = re.search(r"Action:\s*(.*)", content)
            input_match = re.search(r"Action Input:\s*(.*)", content)
            
            if action_match and input_match:
                action = action_match.group(1).strip()
                action_input = input_match.group(1).strip()
                
                observation = ""
                if action == "search_vector_db":
                    observation = self.search_vector_db(action_input)
                elif action == "search_knowledge_graph":
                    observation = self.search_knowledge_graph(action_input)
                elif action == "search_exact_text":
                    observation = self.search_exact_text(action_input)
                else:
                    observation = "Invalid action."
                    
                messages.append({"role": "user", "content": f"Observation:\n{observation}"})
            else:
                # If the LLM didn't format correctly, just try to answer
                return content.strip()
                
        return "I don't know. (Max reasoning steps reached without a Final Answer)"
