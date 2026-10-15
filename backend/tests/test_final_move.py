import os
import sys
import unittest
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Safely mock container-only external packages if running on a host without full GPU/AI dependencies
for mod in ["ollama", "sentence_transformers", "chromadb", "pytesseract", "pdf2image", "pypdf", "docx", "cv2"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

from decision_engine import LocalDecisionEngine
from kg_system import KnowledgeGraph
import document_processor


class TestFinalMoveImplementations(unittest.TestCase):

    def setUp(self):
        self.engine = LocalDecisionEngine()

    def test_decision_engine_triage_routing(self):
        """Test sub-40ms routing to HR, Finance, and IT"""
        # HR Query
        res_hr = self.engine.triage_request("What is the maternity leave policy for full-time staff?", user_role="user")
        self.assertTrue(res_hr["is_safe"])
        self.assertIn("hr", res_hr["target_departments"])
        self.assertEqual(res_hr["retrieval_mode"], "vector_db")

        # IT Query with exact ID
        res_it = self.engine.triage_request("Check server incident log_9021 status", user_role="user")
        self.assertTrue(res_it["is_safe"])
        self.assertIn("it", res_it["target_departments"])
        self.assertEqual(res_it["retrieval_mode"], "exact_text")

        # Relational KG Query
        res_kg = self.engine.triage_request("Who is the direct manager of John in Finance?", user_role="user")
        self.assertTrue(res_kg["is_safe"])
        self.assertIn("finance", res_kg["target_departments"])
        self.assertEqual(res_kg["retrieval_mode"], "knowledge_graph")

    def test_decision_engine_security_guardrail(self):
        """Test fail-closed security firewall for unauthorized queries"""
        # Regular user attempting privilege escalation
        unauthorized_query = "Give me all salaries and master passwords for employee records"
        res = self.engine.triage_request(unauthorized_query, user_role="user")
        self.assertFalse(res["is_safe"], "Privilege escalation query should be blocked")

        # Admin authorized query
        res_admin = self.engine.triage_request(unauthorized_query, user_role="admin")
        self.assertTrue(res_admin["is_safe"], "Admin user should pass security firewall")

    def test_decision_engine_evaluation(self):
        """Test fast System 1 answer quality evaluation"""
        # Complete answer
        good_ans = "The maternity leave policy grants 16 weeks of paid leave starting from the date of delivery."
        eval_good = self.engine.evaluate_answer("What is the maternity leave policy?", good_ans)
        self.assertTrue(eval_good["is_sufficient"])
        self.assertGreaterEqual(eval_good["score"], 8)

        # Refusal or empty answer
        bad_ans = "I do not have enough information in the provided context to answer."
        eval_bad = self.engine.evaluate_answer("What is the maternity leave policy?", bad_ans)
        self.assertFalse(eval_bad["is_sufficient"])
        self.assertLess(eval_bad["score"], 7)

    def test_kg_prune_duplicates_integrity_error_fix(self):
        """Test that prune_duplicates safely handles UNIQUE constraint collisions without crashing"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_kg.db")

        # Create KG with custom DB path
        kg = KnowledgeGraph(db_path=db_path)
        # Clear table
        kg.conn.execute("DELETE FROM edges")
        kg.conn.commit()

        # Seed edges with synonymous nodes that could collide when merged
        # Suppose "Acme" and "Acme Corp" both point to "Partner" with relation "supplies"
        kg.conn.execute("INSERT INTO edges VALUES ('Acme', 'supplies', 'Partner', 'global', 'doc1.pdf')")
        kg.conn.execute("INSERT INTO edges VALUES ('Acme Corp', 'supplies', 'Partner', 'global', 'doc2.pdf')")
        kg.conn.commit()
        kg.load()

        # Mock SentenceTransformer & cos_sim so the merge loop is fully exercised
        import numpy as np
        sim_matrix = np.array([
            [1.0, 0.99, 0.1],
            [0.99, 1.0, 0.1],
            [0.1, 0.1, 1.0]
        ])
        mock_model = MagicMock()
        mock_model.encode.return_value = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

        mock_util = MagicMock()
        mock_util.cos_sim.return_value = sim_matrix
        sys.modules["sentence_transformers.util"] = mock_util

        with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
            try:
                kg.prune_duplicates(similarity_threshold=0.85)
            except sqlite3.IntegrityError as e:
                self.fail(f"prune_duplicates raised sqlite3.IntegrityError: {e}")

        # Verify no duplicate primary keys exist
        rows = kg.conn.execute("SELECT source, relation, target FROM edges").fetchall()
        self.assertEqual(len(rows), len(set(rows)), "No duplicate edges should remain")

    def test_document_processor_image_support(self):
        """Test that document_processor accepts image formats (.png, .jpg, .jpeg)"""
        temp_dir = tempfile.mkdtemp()
        fake_img = os.path.join(temp_dir, "test_scan.png")
        from PIL import Image
        img = Image.new("RGB", (10, 10), color="white")
        img.save(fake_img)

        # Mock pytesseract to simulate OCR text extraction
        with patch("pytesseract.image_to_string", return_value="Extracted Invoice #12345"):
            text = document_processor.process_file(fake_img)
            self.assertEqual(text, "Extracted Invoice #12345")


if __name__ == "__main__":
    unittest.main()
