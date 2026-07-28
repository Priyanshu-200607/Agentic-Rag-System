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

print("All models downloaded and cached successfully.")
