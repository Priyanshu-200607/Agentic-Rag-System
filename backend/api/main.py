"""
FastAPI Application Factory & Ingress Gateway (Hexagonal Ingress).
Assembles routers, middlewares, static asset mounting, and background lifecycles.
"""

import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.middleware.cors_middleware import setup_cors
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.audit_middleware import SecurityAuditMiddleware
from api.routers import auth_router, chat_router, upload_router, admin_router, system_router
from api.dependencies import get_rag_system, get_state_provider

logger = logging.getLogger("rag_system")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Department Agentic RAG Platform",
        version="2.0.0",
        description="Enterprise & HomeLab Agentic RAG with Hexagonal Architecture"
    )

    # 1. Setup Middlewares
    setup_cors(app)
    app.add_middleware(RateLimitMiddleware, max_requests=120, window_seconds=60)
    app.add_middleware(SecurityAuditMiddleware)

    # 2. Register Modular Routers
    app.include_router(auth_router.router)
    app.include_router(chat_router.router)
    app.include_router(upload_router.router)
    app.include_router(admin_router.router)
    app.include_router(system_router.router)

    # 3. Initialize Singletons on Startup
    @app.on_event("startup")
    async def startup_event():
        logger.info("[LIFECYCLE] Initializing database state and vector providers...")
        get_state_provider()
        system = get_rag_system()
        
        # Start nightly pruning if APScheduler is installed
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            scheduler = BackgroundScheduler()
            if hasattr(system, "kg") and system.kg:
                scheduler.add_job(lambda: system.kg.prune_duplicates(), 'cron', hour=3, minute=0)
                scheduler.start()
                logger.info("[LIFECYCLE] Started BackgroundScheduler for nightly KG pruning.")
        except ImportError:
            logger.info("[LIFECYCLE] APScheduler not installed; automated nightly pruning disabled.")

    # 4. Frontend SPA Static Files & Catchall
    frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
    if os.path.exists(frontend_dist):
        app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

        @app.get("/{catchall:path}")
        async def serve_spa(catchall: str):
            file_path = os.path.join(frontend_dist, catchall)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(file_path)
            index_path = os.path.join(frontend_dist, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return {"message": "Multi-Department Agentic RAG Backend API Ready"}

    return app

app = create_app()
