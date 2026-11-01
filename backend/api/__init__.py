"""
API Gateway Package (Hexagonal Ingress).
Exposes FastAPI app instance and factory.
"""

from api.main import app, create_app

__all__ = ["app", "create_app"]
