"""
Integration tests for Document-Level ABAC & Fail-Closed Vector Security.
Verifies role clearance hierarchies, pre-filtering clauses, and leak defenses.
"""

import unittest
from unittest.mock import MagicMock
from core.document_processor import determine_document_access_level
from core.department_agent import DepartmentAgent

class TestABACSecurityIntegration(unittest.TestCase):

    def test_document_classification_mapping(self):
        # 1. Restricted keyword files
        conf, role = determine_document_access_level("master_key_credentials.txt")
        self.assertEqual(conf, "restricted")
        self.assertEqual(role, "admin")

        # 2. Confidential keyword files
        conf, role = determine_document_access_level("employee_salaries_2025.pdf")
        self.assertEqual(conf, "confidential")
        self.assertEqual(role, "manager")

        # 3. Standard internal procedures
        conf, role = determine_document_access_level("office_work_from_home_guidelines.docx")
        self.assertEqual(conf, "internal")
        self.assertEqual(role, "employee")

    def test_abac_query_pre_filtering_defense_in_depth(self):
        mock_client = MagicMock()
        mock_embed = MagicMock()
        mock_embed.encode.return_value.tolist.return_value = [[0.1, 0.2]]

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [
                ["Restricted Master Key: ABC-999", "Manager Payroll Review 2025", "Standard Vacation Policy"]
            ],
            "metadatas": [[
                {"source": "admin_keys.txt", "min_role": "admin", "confidentiality": "restricted"},
                {"source": "payroll_2025.txt", "min_role": "manager", "confidentiality": "confidential"},
                {"source": "vacation.txt", "min_role": "employee", "confidentiality": "internal"}
            ]],
            "distances": [[0.1, 0.2, 0.3]],
            "ids": [["doc_1", "doc_2", "doc_3"]]
        }
        mock_client.get_collection.return_value = mock_collection

        agent = DepartmentAgent("it", client=mock_client, embed_model=mock_embed, llm_model_name="llama3")

        # Scenario 1: Employee queries
        res_emp = agent.search_vector_db("Show credentials and policies", user_role="employee")
        self.assertNotIn("Restricted Master Key", res_emp)
        self.assertNotIn("Manager Payroll", res_emp)
        self.assertIn("Standard Vacation Policy", res_emp)

        # Scenario 2: Manager queries
        res_mgr = agent.search_vector_db("Show credentials and policies", user_role="manager")
        self.assertNotIn("Restricted Master Key", res_mgr)
        self.assertIn("Manager Payroll Review", res_mgr)
        self.assertIn("Standard Vacation Policy", res_mgr)

        # Scenario 3: Admin queries
        res_admin = agent.search_vector_db("Show credentials and policies", user_role="admin")
        self.assertIn("Restricted Master Key", res_admin)
        self.assertIn("Manager Payroll Review", res_admin)
        self.assertIn("Standard Vacation Policy", res_admin)

if __name__ == "__main__":
    unittest.main()
