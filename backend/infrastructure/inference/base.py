"""
Abstract Inference Provider Port (Hexagonal Architecture).
Enables seamless switching between Local Ollama and AWS Cloud vLLM (Continuous Batching).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator

class InferenceProvider(ABC):
    """Abstract interface for LLM inference engines."""

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama3",
        temperature: float = 0.0
    ) -> str:
        """Synchronous chat completion."""
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama3",
        temperature: float = 0.0
    ):
        """Streaming chat completion generator yielding token string chunks."""
        pass
