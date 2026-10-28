import os
import sys
import unittest
import time
import tempfile
from unittest.mock import MagicMock, patch

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Safely mock container-only external packages
for mod in ["ollama", "sentence_transformers", "chromadb", "pytesseract", "pdf2image", "pypdf", "docx", "cv2"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

from auth import (
    hash_password, verify_password,
    generate_sudo_token, verify_sudo_token
)
from audit_logger import log_security_event, AUDIT_LOG_FILE
from hardware_probe import probe_hardware
from reranker import LocalReranker
from hybrid_search import BM25Index, reciprocal_rank_fusion
from document_processor import create_parent_child_chunks
from decision_engine import LocalDecisionEngine

class TestAuthSecurityAndRetrieval(unittest.TestCase):

    def test_cryptographic_password_hashing(self):
        """Test PBKDF2-HMAC-SHA256 password hashing and constant-time verification"""
        password = "SecureEnterprisePassword#2026!"
        hashed = hash_password(password)
        
        self.assertTrue(hashed.startswith("$pbkdf2-sha256$600000$"))
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword123", hashed))
        self.assertFalse(verify_password("", hashed))

    def test_sudo_token_lifecycle(self):
        """Test 5-minute elevated Admin Sudo token generation, validation, and expiry"""
        username = "admin"
        ip = "192.168.1.100"
        token = generate_sudo_token(username, ip)
        
        self.assertTrue(len(token) > 20)
        # Valid verification
        self.assertTrue(verify_sudo_token(token, username=username, ip_address=ip))
        # Wrong username
        self.assertFalse(verify_sudo_token(token, username="hacker", ip_address=ip))
        # Wrong IP
        self.assertFalse(verify_sudo_token(token, username=username, ip_address="10.0.0.1"))
        # Expired token simulation
        from auth import _sudo_tokens, _sudo_lock
        with _sudo_lock:
            _sudo_tokens[token]["expires_at"] = time.time() - 10
        self.assertFalse(verify_sudo_token(token, username=username, ip_address=ip))

    def test_audit_logger(self):
        """Test append-only structured audit logging"""
        log_security_event("TEST_EVENT", "admin", "127.0.0.1", "SUCCESS", {"action": "unit_test"})
        self.assertTrue(os.path.exists(AUDIT_LOG_FILE))
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertTrue(len(lines) > 0)
        import json
        last_event = json.loads(lines[-1])
        self.assertEqual(last_event["event_type"], "TEST_EVENT")
        self.assertEqual(last_event["actor"], "admin")

    def test_hardware_probe(self):
        """Test low-level host discovery and tier classification"""
        profile = probe_hardware()
        self.assertIn("tier", profile)
        self.assertIn("device", profile)
        self.assertIn("cpu_cores", profile)
        self.assertGreater(profile["cpu_cores"], 0)
        self.assertIn("sqlite_cache_kb", profile)
        self.assertIn("thread_tuning", profile)

    def test_bm25_lexical_search_and_rrf(self):
        """Test BM25 index and Reciprocal Rank Fusion hybrid retrieval"""
        docs = [
            {"id": "d1", "text": "Annual leave and paid vacation policy for employees"},
            {"id": "d2", "text": "Database server incident log_9021 connection timeout"},
            {"id": "d3", "text": "Health insurance and medical benefits coverage 2025"}
        ]
        bm25 = BM25Index()
        bm25.fit(docs)
        
        # Exact alphanumeric keyword search
        results = bm25.search("log_9021")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["id"], "d2")
        
        # Test RRF fusion
        dense_results = [{"id": "d1", "text": docs[0]["text"]}]
        fused = reciprocal_rank_fusion(dense_results, results, k=60)
        self.assertTrue(len(fused) >= 2)
        self.assertIn("rrf_score", fused[0])

    def test_cross_encoder_reranker(self):
        """Test candidate cross-scoring reranking"""
        reranker = LocalReranker()
        query = "What is the status of log_9021?"
        candidates = [
            {"id": "1", "text": "Company dress code guidelines.", "distance": 0.5},
            {"id": "2", "text": "Server incident log_9021 has been marked resolved.", "distance": 0.6},
            {"id": "3", "text": "Quarterly financial summary for Q3.", "distance": 0.7}
        ]
        top = reranker.rerank(query, candidates, top_n=1)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]["id"], "2", "Log incident chunk should rank first due to exact identifier match")

    def test_parent_child_chunking(self):
        """Test hierarchical parent-child chunking"""
        long_text = "Section 1: Overview of employee handbook. " * 30
        chunks = create_parent_child_chunks(long_text, source_file="handbook.txt", department="hr")
        self.assertTrue(len(chunks) > 0)
        self.assertIn("parent_id", chunks[0])
        self.assertIn("parent_text", chunks[0])
        self.assertTrue(len(chunks[0]["parent_text"]) >= len(chunks[0]["text"]))

    def test_conversational_query_condensation(self):
        """Test follow-up query condensation using prior chat history"""
        engine = LocalDecisionEngine()
        history = [
            {"sender": "You", "text": "Who is the engineering director?"},
            {"sender": "Assistant", "text": "The engineering director is Alex Chen."}
        ]
        followup = "What about his direct reports?"
        condensed = engine.condense_conversational_query(followup, history)
        self.assertIn("engineering director", condensed.lower())
        self.assertIn("direct reports", condensed.lower())

    def test_zero_trust_empty_allowed_departments(self):
        """Test that empty allowed_departments fails closed immediately without granting fallback depts"""
        engine = LocalDecisionEngine()
        res = engine.triage_request("Where is the office?", user_role="employee", allowed_departments=[])
        self.assertFalse(res["is_safe"], "Empty allowed_departments must fail-closed")
        self.assertEqual(res["target_departments"], [], "Target departments must be empty when no access is allowed")

    def test_document_level_abac_filtering(self):
        """Test Limitation #18 Fix: Document-Level ABAC pre-filtering prevents role data leakage"""
        from department_agent import DepartmentAgent
        mock_client = MagicMock()
        mock_embed = MagicMock()
        mock_embed.encode.return_value.tolist.return_value = [[0.1, 0.2]]
        
        mock_collection = MagicMock()
        # Simulate two documents in DB: one confidential manager salary doc, one standard employee handbook doc
        mock_collection.query.return_value = {
            "documents": [["Executive salary scale 2025: $250k+", "Company general guidelines and dress code"]],
            "metadatas": [[
                {"source": "salaries_2025.pdf", "min_role": "manager", "confidentiality": "confidential"},
                {"source": "handbook.pdf", "min_role": "employee", "confidentiality": "internal"}
            ]],
            "distances": [[0.2, 0.3]],
            "ids": [["doc_salary", "doc_handbook"]]
        }
        mock_client.get_collection.return_value = mock_collection

        agent = DepartmentAgent("hr", mock_client, mock_embed, "llama3")

        # 1. Standard employee querying vector DB: Must NOT see salary doc
        res_employee = agent.search_vector_db("Show me salaries and policies", user_role="employee")
        self.assertNotIn("Executive salary scale", res_employee, "Standard employee must NOT retrieve manager-only salary document")
        self.assertIn("Company general guidelines", res_employee)

        # 2. Manager querying vector DB: Must see both salary and general policies
        res_manager = agent.search_vector_db("Show me salaries and policies", user_role="manager")
        self.assertIn("Executive salary scale", res_manager, "Manager must be permitted to retrieve manager-level documents")
        self.assertIn("Company general guidelines", res_manager)

    def test_sudo_barrier_destructive_operations_enforcement(self):
        """Test that high-privilege operations require elevated sudo token"""
        from auth import check_admin_sudo_barrier
        
        # Test 1: Valid sudo token succeeds
        valid_token = generate_sudo_token("admin", "192.168.1.50")
        allowed, err = check_admin_sudo_barrier("admin", sudo_token=valid_token, ip_address="192.168.1.50")
        self.assertTrue(allowed)
        self.assertEqual(err, "")

        # Test 2: Invalid sudo token fails
        allowed, err = check_admin_sudo_barrier("admin", sudo_token="invalid_token_xyz", ip_address="192.168.1.50")
        self.assertFalse(allowed)
        self.assertIn("invalid or expired", err)

        # Test 3: Sudo token from wrong IP fails
        allowed, err = check_admin_sudo_barrier("admin", sudo_token=valid_token, ip_address="10.0.0.99")
        self.assertFalse(allowed)

        # Test 4: Missing token when enforce=True fails
        allowed, err = check_admin_sudo_barrier("admin", sudo_token=None, ip_address="192.168.1.50", enforce=True)
        self.assertFalse(allowed)
        self.assertIn("Sudo token required", err)

    def test_setup_admin_cli_and_lockdown(self):
        from scripts.setup_admin import configure_admin_password
        from auth import load_db, verify_password
        
        # Test 1: Password too short fails
        self.assertFalse(configure_admin_password("short", force=True))
        
        # Test 2: Valid setup succeeds
        self.assertTrue(configure_admin_password("SuperSecretAdminPass123!", force=True))
        db = load_db()
        self.assertTrue(db.get("setup_completed"))
        admin_hash = db["users"]["admin"]["password_hash"]
        self.assertTrue(verify_password("SuperSecretAdminPass123!", admin_hash))
        
        # Test 3: Re-running without force fails
        self.assertFalse(configure_admin_password("AnotherPass12345!", force=False))
        # Ensure password was NOT modified
        db = load_db()
        self.assertTrue(verify_password("SuperSecretAdminPass123!", db["users"]["admin"]["password_hash"]))
        
        # Test 4: Re-running with force succeeds
        self.assertTrue(configure_admin_password("AnotherPass12345!", force=True))
        db = load_db()
        self.assertTrue(verify_password("AnotherPass12345!", db["users"]["admin"]["password_hash"]))


if __name__ == "__main__":
    unittest.main()

