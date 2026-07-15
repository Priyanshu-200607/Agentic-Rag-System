import sys
import os
import chromadb
from ollama import chat
from chromadb.utils import embedding_functions
from kg_system import KnowledgeGraph

query = """User_213 appears in records across multiple departments. Compile a complete profile of this user by finding: 1. All leave requests filed by User_213 (HR) — types and total days 2. All hardware requests made by User_213 (IT) — items requested and their statuses 3. All expense reports submitted by User_213 (Finance) — categories and approval statuses Then, considering that HR policy caps sick leave at 10 days/year, assess whether User_213's total benefit usage across departments suggests any compliance concerns or patterns worth flagging."""

print("--- DEBUGGING VECTOR DB ---")
client = chromadb.PersistentClient(path="./chroma_db_multi")
embed_model = embedding_functions.DefaultEmbeddingFunction()

query_embedding = embed_model([query])
for dept in ["hr", "it", "finance"]:
    try:
        col = client.get_collection(name=dept)
        res = col.query(query_embeddings=query_embedding, n_results=3)
        print(f"\nDistances for {dept}:")
        print(res['distances'][0])
    except Exception as e:
        print(f"Failed to query {dept}: {e}")

print("\n--- DEBUGGING KNOWLEDGE GRAPH ---")
kg = KnowledgeGraph()
print("\nExtracting entities from query...")
import config
entities = kg._extract_entities_cached(query, config.LLM_MODEL_NAME)
print(f"Extracted Entities: {entities}")

print("\nCanonicalizing entities...")
resolved = set()
for raw in entities:
    canonical = kg.canonicalize(raw)
    resolved.add(canonical)
    for token in canonical.split():
        if len(token) > 3:
            resolved |= kg.fuzzy_find_nodes(token)
print(f"Resolved Nodes: {resolved}")
