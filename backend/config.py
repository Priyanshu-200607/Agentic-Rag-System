import os

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

# --- MODEL CONFIGURATION ---
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama3")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", os.path.join(os.path.dirname(os.path.abspath(__file__)), "embedding_model"))
KG_MODEL_NAME = os.getenv("KG_MODEL_NAME", "Babelscape/rebel-large")
ADAPTIVE_KG_EXTRACTION = True # If True, use LLM for extraction when VRAM is high, else fallback to REBEL

# --- PATH CONFIGURATION ---
EDITION = os.getenv("APP_EDITION", "opensource")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(BASE_DIR, "chroma_db_multi"))
KG_DB_PATH = os.getenv("KG_DB_PATH", os.path.join(BASE_DIR, "knowledge_graph.db"))
AUTH_DB_PATH = os.getenv("AUTH_DB_PATH", os.path.join(BASE_DIR, "db.json"))
STATE_DB_PATH = os.getenv("STATE_DB_PATH", os.path.join(BASE_DIR, "state.db"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))
HISTORY_FILE_PATH = os.getenv("HISTORY_FILE_PATH", os.path.join(BASE_DIR, "history.json"))
ENTITIES_CONFIG_PATH = os.getenv("ENTITIES_CONFIG_PATH", os.path.join(BASE_DIR, "entities.json"))

# --- SECURITY CONFIGURATION ---
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# --- RAG LIMITS ---
HISTORY_MAX_ENTRIES = int(os.getenv("HISTORY_MAX_ENTRIES", "500"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "8000"))
MAX_QUERY_CHARS = int(os.getenv("MAX_QUERY_CHARS", "2000"))
MAX_KG_FACTS = int(os.getenv("MAX_KG_FACTS", "30"))
MAX_KG_HOPS = int(os.getenv("MAX_KG_HOPS", "2"))
