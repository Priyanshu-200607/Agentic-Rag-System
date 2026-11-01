"""
API Gateway Facade.
Re-exports FastAPI app instance from api.main for backward compatibility.
Run: uvicorn api:app --host 0.0.0.0 --port 8000
"""

from api.main import app
