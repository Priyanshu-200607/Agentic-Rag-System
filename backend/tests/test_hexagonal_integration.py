"""
End-to-End Hexagonal Architecture Integration Tests.
Verifies collaboration between Core Orchestrator, StorageProvider, StateProvider,
DecisionEngine, and DepartmentAgent with zero circular dependencies.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from core.orchestrator import MultiDeptRAG
from core.schemas import User
from infrastructure.storage.local_storage import LocalDiskStorageProvider
from infrastructure.state.sqlite_state import SQLiteStateProvider
from core.decision_engine import LocalDecisionEngine

class TestHexagonalIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_state.db")
        self.upload_dir = os.path.join(self.temp_dir.name, "uploads")

        self.state_provider = SQLiteStateProvider(db_path=self.db_path)
        self.storage_provider = LocalDiskStorageProvider(base_dir=self.upload_dir)
        self.decision_engine = LocalDecisionEngine()

        # Seed test user
        self.test_user = User(
            username="tester_john",
            role="employee",
            status="active",
            allowed_departments=["hr", "it"]
        )
        self.state_provider.save_user(self.test_user)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_storage_provider_file_lifecycle(self):
        content = b"Confidential remote work policy 2026: Friday WFH permitted."
        saved_path = self.storage_provider.save_file("hr", "remote_policy.txt", content)

        self.assertTrue(os.path.exists(saved_path))
        read_back = self.storage_provider.read_file("hr", "remote_policy.txt")
        self.assertEqual(read_back, content)

        file_list = self.storage_provider.list_files("hr")
        self.assertIn("remote_policy.txt", file_list)

        self.storage_provider.delete_file("hr", "remote_policy.txt")
        self.assertNotIn("remote_policy.txt", self.storage_provider.list_files("hr"))

    def test_decision_engine_triage_routing(self):
        # HR Query
        triage_hr = self.decision_engine.triage_request(
            "What is the vacation policy for new hires?",
            user_role="employee",
            allowed_departments=["hr", "it"]
        )
        self.assertTrue(triage_hr["is_safe"])
        self.assertIn("hr", triage_hr["target_departments"])

        # IT Query with ticket ID
        triage_it = self.decision_engine.triage_request(
            "Check status of log_9021 server ticket",
            user_role="employee",
            allowed_departments=["hr", "it"]
        )
        self.assertTrue(triage_it["is_safe"])
        self.assertIn("it", triage_it["target_departments"])
        self.assertEqual(triage_it["retrieval_mode"], "exact_text")

    def test_orchestrator_process_request_flow(self):
        mock_vec = MagicMock()
        mock_graph = MagicMock()
        mock_inf = MagicMock()
        mock_inf.chat.return_value = "Employees receive 20 days paid leave per calendar year."

        rag = MultiDeptRAG(
            state_provider=self.state_provider,
            storage_provider=self.storage_provider,
            vector_provider=mock_vec,
            graph_provider=mock_graph,
            inference_provider=mock_inf,
            decision_engine=self.decision_engine
        )

        # Mock agent query on department agent
        hr_agent = rag.get_agent("hr")
        with patch.object(hr_agent, "query", return_value="Employees receive 20 days paid leave per calendar year."):
            chunks = list(rag.process_request("What is the leave policy?", username="tester_john"))
            self.assertTrue(len(chunks) > 0)
            combined = "".join(chunks)
            self.assertIn("Routing query", combined)
            self.assertIn("20 days paid leave", combined)

if __name__ == "__main__":
    unittest.main()
