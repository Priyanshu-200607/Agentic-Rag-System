"""
Chat & Conversation Router (Hexagonal Ingress).
Streams multi-department RAG responses and manages conversation sessions.
"""

import uuid
import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from fastapi.responses import StreamingResponse

from core.schemas import Question
from infrastructure.state.base import StateProvider
from api.dependencies import get_state_provider, get_rag_system
from platform_runtime.audit_ledger import log_security_event

logger = logging.getLogger("rag_system")
router = APIRouter(tags=["Chat"])

@router.post("/api/chat")
@router.post("/chat")
def chat(
    req: Question,
    request: Request,
    x_username: Optional[str] = Header(None),
    state: StateProvider = Depends(get_state_provider),
    system = Depends(get_rag_system)
):
    session_id = req.session_id or uuid.uuid4().hex
    client_ip = request.client.host if request.client else "unknown"
    effective_username = req.username or x_username

    if not effective_username:
        log_security_event("UNAUTHORIZED_CHAT", "anonymous", client_ip, "DENIED", {"reason": "missing_username"})
        return StreamingResponse(
            iter([json.dumps({"type": "answer", "message": "Error: Unauthorized access. Please log in."}) + "\n"]),
            media_type="application/x-ndjson"
        )

    user = state.get_user(effective_username)
    if not user:
        log_security_event("UNAUTHORIZED_CHAT", effective_username, client_ip, "DENIED", {"reason": "user_not_found"})
        return StreamingResponse(
            iter([json.dumps({"type": "answer", "message": "Error: User account not found."}) + "\n"]),
            media_type="application/x-ndjson"
        )

    if user.status == "suspended":
        log_security_event("SUSPENDED_CHAT", effective_username, client_ip, "BLOCKED", {"reason": "account_suspended"})
        return StreamingResponse(
            iter([json.dumps({"type": "answer", "message": "Error: Your account is suspended. Contact an administrator."}) + "\n"]),
            media_type="application/x-ndjson"
        )

    # System 1 Non-autoregressive triage & firewall check
    triage = system.decision_engine.triage_request(
        req.question,
        user_role=user.role,
        allowed_departments=user.allowed_departments
    )
    if not triage.get("is_safe", True):
        log_security_event("FIREWALL_QUERY_BLOCKED", effective_username, client_ip, "BLOCKED", {"query": req.question[:100], "role": user.role})
        return StreamingResponse(
            iter([json.dumps({"type": "answer", "message": "Error: Unauthorized access detected by security firewall."}) + "\n"]),
            media_type="application/x-ndjson"
        )

    # Fetch past conversation turns for query condensation
    past_messages = state.get_chat_history(effective_username, session_id)

    def generate():
        final_answer = "Error generating response."
        for chunk in system.process_request(req.question, username=effective_username, chat_history=past_messages):
            yield chunk
            try:
                data = json.loads(chunk.strip())
                if data.get("type") == "answer":
                    final_answer = data.get("message", "")
            except Exception:
                pass

        # Save conversation to persistent SQLite StateProvider
        state.append_chat_message(effective_username, session_id, {
            "sender": "You",
            "text": req.question,
            "role": "user"
        })
        state.append_chat_message(effective_username, session_id, {
            "sender": "Assistant",
            "text": final_answer,
            "role": "assistant"
        })

    return StreamingResponse(generate(), media_type="application/x-ndjson")

@router.get("/api/chat/sessions")
@router.get("/chat/sessions")
def get_sessions(
    username: Optional[str] = None,
    x_username: Optional[str] = Header(None),
    state: StateProvider = Depends(get_state_provider)
):
    effective_username = x_username or username
    if not effective_username:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return state.get_chat_sessions(effective_username)

@router.get("/api/chat/session/{session_id}")
@router.get("/chat/session/{session_id}")
def get_session(
    session_id: str,
    username: Optional[str] = None,
    x_username: Optional[str] = Header(None),
    state: StateProvider = Depends(get_state_provider)
):
    effective_username = x_username or username
    if not effective_username:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return state.get_chat_history(effective_username, session_id)

@router.post("/api/chat/session")
@router.post("/chat/session")
def create_session(
    username: Optional[str] = None,
    x_username: Optional[str] = Header(None),
    state: StateProvider = Depends(get_state_provider)
):
    effective_username = x_username or username
    if not effective_username:
        raise HTTPException(status_code=401, detail="Authentication required.")
    session_id = uuid.uuid4().hex
    state.create_chat_session(effective_username, session_id, title="New Chat")
    return {"session_id": session_id}

@router.delete("/api/chat/session/{session_id}")
@router.delete("/chat/session/{session_id}")
def delete_session(
    session_id: str,
    username: Optional[str] = None,
    x_username: Optional[str] = Header(None),
    state: StateProvider = Depends(get_state_provider)
):
    effective_username = x_username or username
    if not effective_username:
        raise HTTPException(status_code=401, detail="Authentication required.")
    success = state.delete_chat_session(effective_username, session_id)
    return {"success": success}
