"""
Abstract State Provider Port (Hexagonal Architecture).
Enables seamless switching between Embedded SQLite (WAL) and Amazon Aurora / PostgreSQL.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from core.schemas import User, ChatSession, ChatMessage, SudoSession

class StateProvider(ABC):
    """Abstract interface for application state, users, permissions, chat history, and sudo tokens."""

    # --- USER OPERATIONS ---
    @abstractmethod
    def get_user(self, username: str) -> Optional[User]:
        pass

    @abstractmethod
    def save_user(self, user: User) -> None:
        pass

    @abstractmethod
    def delete_user(self, username: str) -> bool:
        pass

    @abstractmethod
    def list_users(self) -> List[User]:
        pass

    # --- DEPARTMENT OPERATIONS ---
    @abstractmethod
    def get_department(self, name: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_department(self, name: str, status: str = "active") -> None:
        pass

    @abstractmethod
    def delete_department(self, name: str) -> bool:
        pass

    @abstractmethod
    def list_departments(self) -> Dict[str, Dict[str, Any]]:
        pass

    # --- CHAT & SESSION OPERATIONS ---
    @abstractmethod
    def create_chat_session(self, username: str, session_id: str, title: str = "New Chat") -> str:
        pass

    @abstractmethod
    def get_chat_sessions(self, username: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_chat_history(self, username: str, session_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def append_chat_message(self, username: str, session_id: str, message: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def delete_chat_session(self, username: str, session_id: str) -> bool:
        pass

    # --- SUDO SESSIONS ---
    @abstractmethod
    def save_sudo_session(self, sudo_session: SudoSession) -> None:
        pass

    @abstractmethod
    def get_sudo_session(self, token: str) -> Optional[SudoSession]:
        pass

    @abstractmethod
    def delete_sudo_session(self, token: str) -> None:
        pass

    # --- SETUP / SYSTEM STATE ---
    @abstractmethod
    def get_setup_status(self) -> bool:
        pass

    @abstractmethod
    def set_setup_completed(self, completed: bool = True) -> None:
        pass
