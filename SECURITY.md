# Security Policy

AegisRAG is designed from the ground up for zero-trust, air-gapped, and high-compliance enterprise environments. We take the security, integrity, and privacy of your organizational data seriously.

This document outlines our security policies, supported versions, threat model, and instructions for reporting vulnerabilities.

---

## Supported Versions

Security updates, vulnerability patches, and cryptographic errata are actively maintained for the following versions:

| Version | Release Series | Security Support Status |
|:---|:---|:---|
| **2.x.x** | Hexagonal Enterprise Platform | ✅ **Actively Supported** |
| 1.x.x | Monolithic Prototype | ❌ End of Life (Deprecated) |

---

## Reporting a Vulnerability

We practice **Coordinated Vulnerability Disclosure**. If you believe you have found a security vulnerability in AegisRAG, please do **NOT** open a public issue on GitHub. Public disclosure before remediation puts regulated production environments at risk.

### Responsible Disclosure Process:

1. **Email Advisory**: Send a detailed advisory report to the security team at **security@aegisrag.internal** (or contact repository maintainers directly via GitHub Private Vulnerability Reporting).
2. **Details to Include**:
   * Type of vulnerability (e.g., ABAC privilege escalation, JWT tampering, prompt injection escape, timing side-channel).
   * Exact steps to reproduce the issue (PoC scripts or HTTP requests).
   * Affected endpoints, files, or infrastructure adapters.
   * Potential impact and proposed remediation (if available).
3. **Response Timeline (SLA)**:
   * **Initial Acknowledgment**: Within **24 hours**.
   * **Severity & Triage Assessment**: Within **48 hours**.
   * **Patch Release & Advisory Notice**: Within **7 to 14 days** depending on vulnerability criticality.

We will acknowledge your contributions in our security release notes (unless you request anonymity).

---

## Security Architecture & Threat Model

AegisRAG enforces a defense-in-depth security perimeter across physical, logical, and algorithmic layers:

```
+-----------------------------------------------------------------------------------+
|                            LAYER 1: ZERO-TRUST INGRESS                            |
|  - RFC 7519 OAuth2 JWT Bearer Tokens with HMAC-SHA256 signature verification       |
|  - Fail-closed access gates: Missing / unauthenticated requests reject with 401   |
|  - Token-bucket rate limiting per IP and authenticated actor                      |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        LAYER 2: PARTITIONED RBAC & ABAC                           |
|  - Department-Level RBAC: Access restricted to authorized department sets         |
|  - Document-Level ABAC: Sensitivity tags (restricted, confidential, internal)     |
|  - Database Pre-Filtering: Enforced inside ChromaDB queries and BM25 postings    |
|  - In-Memory Defense: Ineligible documents never enter prompt context              |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     LAYER 3: DESTRUCTIVE ACTION SUDO BARRIER                      |
|  - Administrative operations require a 5-minute elevated cryptographic token      |
|  - Cryptographically bound to client IP, expiration timestamp, and HMAC signature |
|  - Auto-purged upon expiration or tamper detection                                |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     LAYER 4: PROMPT INJECTION & JAILBREAK GUARD                   |
|  - Retrieved content strictly encapsulated in <document_context> XML tags         |
|  - System directives enforce passive reference treatment of retrieved texts      |
|  - Cross-encoder reranker winnows injected adversarial noise                     |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                  LAYER 5: TAMPER-EVIDENT HASH-CHAIN AUDIT LEDGER                  |
|  - Append-only cryptographic ledger (security_audit.jsonl)                        |
|  - Record hash: SHA256(prev_hash || timestamp || event || actor || IP || details)|
|  - In-process mathematical verification detects truncation, modification, or wipe |
+-----------------------------------------------------------------------------------+
```

---

## Cryptographic Standards

AegisRAG relies exclusively on industry-standard, battle-tested cryptographic primitives implemented via audited standard libraries:

* **Password Hashing**: PBKDF2-HMAC-SHA256 with **600,000 iterations** and 16-byte cryptographically secure random salts (`secrets.token_bytes(16)`). Constant-time comparisons (`hmac.compare_digest`) prevent timing analysis.
* **Token Assertion**: RFC 7519 JSON Web Tokens (JWT) signed with HMAC-SHA256 using persistent 32-byte secret keys.
* **Sudo Authorization**: Persistent MAC signatures generated over `user_id || client_ip || issued_at || expires_at`.
* **Audit Integrity**: Unbroken SHA-256 hash chaining guaranteeing mathematical detection of retrospective log alteration.

---

## Best Practices for Secure Enterprise Deployment

1. **Air-Gapped Operation**: Run containers with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. Models must be pre-cached to eliminate outbound internet egress.
2. **Secret Management**: Never commit your `.env` file to version control. Set `JWT_SECRET_KEY` via enterprise secret managers (AWS Secrets Manager, HashiCorp Vault, or Docker Secrets).
3. **Admin Password Provisioning**: Immediately rotate default administrator passwords during initial deployment using `python3 backend/scripts/setup_admin.py --force`.
4. **Least-Privilege Tenancy**: Assign users only to necessary departmental partitions. Never grant `admin` roles to regular query consumers.
