"""
Token-bucket rate limiter middleware per IP / User.
Protects local and cloud deployments from denial-of-service query flooding.
"""

import time
import threading
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: Dict[str, Tuple[int, float]] = {}
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Exempt static assets and health checks
        path = request.url.path
        if path.startswith("/assets") or path == "/api/system/status" or path == "/favicon.ico":
            return await call_next(request)

        with self._lock:
            # Clean expired clients periodically
            if len(self.clients) > 1000:
                self.clients = {ip: (cnt, exp) for ip, (cnt, exp) in self.clients.items() if now < exp}

            count, expiry = self.clients.get(client_ip, (0, now + self.window_seconds))
            if now > expiry:
                count = 0
                expiry = now + self.window_seconds

            if count >= self.max_requests:
                raise HTTPException(status_code=429, detail="Too Many Requests: Rate limit exceeded. Try again later.")

            self.clients[client_ip] = (count + 1, expiry)

        return await call_next(request)
