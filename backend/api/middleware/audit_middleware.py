"""
Audit middleware for logging sensitive administrative and auth actions to the cryptographic ledger.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from platform_runtime.audit_ledger import log_security_event

class SecurityAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Log 401 and 403 authorization failures automatically
        if response.status_code in (401, 403):
            client_ip = request.client.host if request.client else "unknown"
            log_security_event(
                "HTTP_AUTH_DENIED",
                username="anonymous",
                client_ip=client_ip,
                status="DENIED",
                details={"path": str(request.url.path), "status_code": response.status_code, "method": request.method}
            )
            
        return response
