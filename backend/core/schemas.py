"""
Pure Pydantic v2 domain schemas for Multi-Department Agentic RAG.
Zero database, network, or cloud lock-in.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- AUTH & USER SCHEMAS ---

class User(BaseModel):
    username: str
    role: str = "employee"  # "admin", "manager", "employee", "user"
    status: str = "active"  # "active", "suspended"
    allowed_departments: List[str] = Field(default_factory=list)
    password_hash: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "employee"
    allowed_departments: List[str] = Field(default_factory=list)

class UserUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None
    allowed_departments: Optional[List[str]] = None
    password: Optional[str] = None

class AccessUpdate(BaseModel):
    allowed_departments: List[str]

class Login(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes
    refresh_token: Optional[str] = None
    username: str
    role: str
    allowed_departments: List[str] = Field(default_factory=list)
    setup_completed: bool = True

class TokenPayload(BaseModel):
    sub: str  # username
    role: str = "employee"
    allowed_departments: List[str] = Field(default_factory=list)
    exp: int
    iat: Optional[int] = None
    scope: str = "access"

# --- SUDO & SETUP SCHEMAS ---

class SudoVerifyRequest(BaseModel):
    username: str
    password: str

class SudoTokenResponse(BaseModel):
    success: bool = True
    sudo_token: str
    expires_in: int = 300  # 5 minutes
    message: str = "Sudo privileges granted for 5 minutes."

class SudoSession(BaseModel):
    token: str
    username: str
    ip_address: str = ""
    issued_at: float
    expires_at: float
    signature: str = ""
    scope: str = "elevated_admin_action"

class SetupRequest(BaseModel):
    admin_password: str

class SetupStatus(BaseModel):
    setup_completed: bool = False

# --- CHAT & CONVERSATION SCHEMAS ---

class Question(BaseModel):
    question: str
    username: Optional[str] = None
    session_id: Optional[str] = None

class ChatMessage(BaseModel):
    id: Optional[str] = None
    sender: str  # "You" or "Assistant"
    text: str
    timestamp: Optional[str] = None
    role: Optional[str] = None

class ChatSession(BaseModel):
    session_id: str
    user_id: str
    title: str = "New Chat"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)

# --- INGESTION & DOCUMENT SCHEMAS ---

class DocumentChunk(BaseModel):
    id: str
    text: str
    parent_id: Optional[str] = None
    parent_text: Optional[str] = None
    source: str = ""
    department: str = ""
    confidentiality: str = "internal"  # "restricted", "confidential", "internal", "public"
    min_role: str = "employee"        # "admin", "manager", "employee"

class Upload(BaseModel):
    department: str
    file_paths: List[str]

class UploadResponse(BaseModel):
    status: str
    message: str
    files_processed: int = 0
    total_chunks: int = 0

# --- RETRIEVAL & SEARCH SCHEMAS ---

class ChunkMatch(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    distance: float = 0.0
    relevance_score: Optional[float] = None
    lexical_score: Optional[float] = None
    rrf_score: Optional[float] = None

class TriageDecision(BaseModel):
    is_safe: bool = True
    target_departments: List[str] = Field(default_factory=list)
    retrieval_mode: str = "vector_db"  # "vector_db", "knowledge_graph", "exact_text"
    confidence: float = 0.95
    extracted_entity: str = ""

class AnswerEvaluation(BaseModel):
    score: int = 8
    is_sufficient: bool = True
    feedback: str = ""

# --- DEPARTMENT & SYSTEM SCHEMAS ---

class Department(BaseModel):
    name: str
    status: str = "active"  # "active", "suspended"
    document_count: int = 0
    created_at: Optional[str] = None

class LLMConfig(BaseModel):
    current_model: str
    temperature: float = 0.0
    available_models: List[str] = Field(default_factory=list)

class LLMConfigUpdate(BaseModel):
    model_name: str

class SecurityEvent(BaseModel):
    timestamp: str
    event_type: str
    username: str
    client_ip: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)
    prev_hash: Optional[str] = None
    record_hash: Optional[str] = None
