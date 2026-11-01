"""
Local Ollama Inference Provider Adapter.
Communicates with the local Ollama instance for LLM synthesis.
"""

import logging
from typing import List, Dict, Any, Generator
from infrastructure.inference.base import InferenceProvider
import config

logger = logging.getLogger("rag_system")

class OllamaInferenceProvider(InferenceProvider):
    """Local Ollama implementation of InferenceProvider."""

    def __init__(self, default_model: str = None):
        self.default_model = default_model or getattr(config, "LLM_MODEL_NAME", "llama3")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.0
    ) -> str:
        selected_model = model or self.default_model
        try:
            from ollama import chat
            response = chat(
                model=selected_model,
                messages=messages,
                options={"temperature": temperature}
            )
            if hasattr(response, "message") and hasattr(response.message, "content"):
                return response.message.content.strip()
            elif isinstance(response, dict):
                return response.get("message", {}).get("content", "").strip()
            return str(response).strip()
        except Exception as e:
            logger.error(f"[OLLAMA] Chat generation failed: {e}")
            return f"Error connecting to local LLM ({selected_model}): {e}"

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.0
    ) -> Generator[str, None, None]:
        selected_model = model or self.default_model
        try:
            from ollama import chat
            stream = chat(
                model=selected_model,
                messages=messages,
                stream=True,
                options={"temperature": temperature}
            )
            for chunk in stream:
                if hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                    yield chunk.message.content
                elif isinstance(chunk, dict):
                    yield chunk.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"[OLLAMA] Streaming failed: {e}")
            yield f"Error in streaming generation: {e}"
