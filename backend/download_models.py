import os
from huggingface_hub import snapshot_download
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from sentence_transformers import SentenceTransformer

# 1. Download Embedding Model
embed_model = "BAAI/bge-small-en-v1.5"
print(f"Downloading {embed_model}...")
SentenceTransformer(embed_model)

# 2. Download REBEL KG Model
kg_model = "Babelscape/rebel-large"
print(f"Downloading {kg_model}...")
snapshot_download(repo_id=kg_model)
AutoTokenizer.from_pretrained(kg_model)
AutoModelForSeq2SeqLM.from_pretrained(kg_model)

# 3. Download Deduplication & Fast Routing Model
minilm_model = "all-MiniLM-L6-v2"
print(f"Downloading {minilm_model}...")
SentenceTransformer(minilm_model)

# 4. Download Cross-Encoder Reranker Model
try:
    from sentence_transformers import CrossEncoder
    reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    print(f"Downloading {reranker_model}...")
    CrossEncoder(reranker_model)
except Exception as e:
    print(f"Warning: Could not pre-cache CrossEncoder: {e}")

print("All models downloaded and cached successfully.")
