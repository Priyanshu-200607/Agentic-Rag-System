"""
Pytest configuration and environment fixture setup.
Ensures backend directory is on sys.path for all integration tests.
"""

import os
import sys

# Insert backend directory into sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Safely mock container-only external packages if running on a host without full GPU/AI dependencies
for mod in ["ollama", "sentence_transformers", "chromadb", "pytesseract", "pdf2image", "pypdf", "docx", "cv2"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            from unittest.mock import MagicMock
            sys.modules[mod] = MagicMock()
