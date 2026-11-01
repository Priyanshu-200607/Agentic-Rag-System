"""
Audit Logger Facade.
Delegates to platform_runtime.audit_ledger for cryptographic SHA-256 hash chaining.
"""

from platform_runtime.audit_ledger import (
    log_security_event,
    get_audit_ledger,
    AUDIT_LOG_FILE
)
