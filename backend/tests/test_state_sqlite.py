"""
Integration tests for SQLiteStateProvider (WAL mode).
Validates multi-user management, chat history, and department status transitions.
"""

import os
import tempfile
import unittest
from core.schemas import User
from infrastructure.state.sqlite_state import SQLiteStateProvider

class TestStateSQLiteIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_state.db")
        self.state = SQLiteStateProvider(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_user_lifecycle_crud(self):
        # 1. Create User
        user = User(
            username="eng_lead",
            role="manager",
            status="active",
            allowed_departments=["it", "engineering"]
        )
        self.state.save_user(user)

        # 2. Read User
        fetched = self.state.get_user("eng_lead")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.username, "eng_lead")
        self.assertEqual(fetched.role, "manager")
        self.assertEqual(fetched.allowed_departments, ["it", "engineering"])

        # 3. Update User
        fetched.status = "suspended"
        self.state.save_user(fetched)
        updated = self.state.get_user("eng_lead")
        self.assertEqual(updated.status, "suspended")

        # 4. Delete User
        self.assertTrue(self.state.delete_user("eng_lead"))
        self.assertIsNone(self.state.get_user("eng_lead"))

    def test_department_crud(self):
        self.state.save_department("legal", status="active")
        dept = self.state.get_department("legal")
        self.assertIsNotNone(dept)
        self.assertEqual(dept["status"], "active")

        # Toggle suspend
        self.state.save_department("legal", status="suspended")
        dept_updated = self.state.get_department("legal")
        self.assertEqual(dept_updated["status"], "suspended")

        # Delete department
        self.assertTrue(self.state.delete_department("legal"))
        self.assertIsNone(self.state.get_department("legal"))

    def test_chat_session_and_message_persistence(self):
        user = User(username="chatter", role="employee", status="active", allowed_departments=["hr"])
        self.state.save_user(user)

        session_id = "sess_001"
        self.state.create_chat_session("chatter", session_id, title="Benefits Query")

        # Append messages
        self.state.append_chat_message("chatter", session_id, {"sender": "You", "text": "What is health policy?", "role": "user"})
        self.state.append_chat_message("chatter", session_id, {"sender": "Assistant", "text": "Coverage is 100%.", "role": "assistant"})

        history = self.state.get_chat_history("chatter", session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["sender"], "You")
        self.assertEqual(history[1]["sender"], "Assistant")

        # Delete session cascades
        self.assertTrue(self.state.delete_chat_session("chatter", session_id))
        self.assertEqual(len(self.state.get_chat_history("chatter", session_id)), 0)

    def test_setup_status_transition(self):
        self.state.set_setup_completed(False)
        self.assertFalse(self.state.get_setup_status())
        self.state.set_setup_completed(True)
        self.assertTrue(self.state.get_setup_status())

if __name__ == "__main__":
    unittest.main()
