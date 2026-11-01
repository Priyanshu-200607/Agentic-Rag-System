"""
CORS Middleware Configuration.
"""

from fastapi.middleware.cors import CORSMiddleware
import config

def setup_cors(app):
    origins = getattr(config, "CORS_ORIGINS", ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
