import os
import sys
import unittest
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

from decision_engine import LocalDecisionEngine
from department_agent import DepartmentAgent


class TestAgentAndOrchestrator(unittest.TestCase):

    def setUp(self):
        self.decision_engine = LocalDecisionEngine()
        self.mock_client = MagicMock()
        self.mock_embed = MagicMock()
        self.mock_kg = MagicMock()
        self.agent = DepartmentAgent(
            department_name="hr",
            client=self.mock_client,
            embed_model=self.mock_embed,
            llm_model_name="llama3",
            kg=self.mock_kg,
            decision_engine=self.decision_engine
        )

    def test_search_vector_db_receives_full_query(self):
        """Fix B4: Vector DB search must receive the entire conversational query, not just a single entity"""
        full_query = "What are the specific employee benefits and 401k matching percentages for senior engineers in 2025?"
        
        # Mock search_vector_db on agent
        with patch.object(self.agent, "search_vector_db", return_value="[Source: hr_2025.txt]\n401k match is 6%.") as mock_search_vec:
            with patch("department_agent.chat") as mock_chat:
                mock_chat.return_value.message.content = "401k match is 6%."
                
                resp = self.agent.query(full_query)
                self.assertEqual(resp, "401k match is 6%.")
                
                # Check that search_vector_db was invoked with full_query!
                mock_search_vec.assert_called()
                called_query = mock_search_vec.call_args[0][0]
                self.assertEqual(called_query, full_query, "search_vector_db must receive the complete query to preserve semantic embedding quality")

    def test_routing_sub_millisecond(self):
        """Verify that routing executes in sub-millisecond time without LLM generation delays"""
        import time
        allowed = ["hr", "finance", "it"]
        
        start = time.perf_counter()
        triage = self.decision_engine.triage_request("Where do I submit my expense report for travel reimbursement?", allowed_departments=allowed)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        self.assertLess(elapsed_ms, 50, f"Routing took {elapsed_ms:.2f}ms; target is < 50ms")
        self.assertIn("finance", triage["target_departments"])
        self.assertEqual(triage["retrieval_mode"], "vector_db")


if __name__ == "__main__":
    unittest.main()
