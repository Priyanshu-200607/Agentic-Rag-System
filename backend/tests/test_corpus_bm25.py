"""
Test Suite for True Corpus-Wide Inverted BM25 Index & Hybrid Search.
Verifies exact keyword matching, rare identifier retrieval (log_9021, req-4402),
disk persistence, incremental indexing, and Document-Level ABAC pre-filtering.
"""

import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.hybrid_retriever import BM25Index, CorpusBM25Index, reciprocal_rank_fusion
from core.department_agent import DepartmentAgent

class TestCorpusBM25Index(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bm25_index = CorpusBM25Index(storage_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_exact_rare_identifier_retrieval(self):
        """Verifies that rare technical identifiers like log_9021 are retrieved with highest score."""
        chunks = [
            {
                "id": "c1",
                "text": "Regular server maintenance scheduled for Friday evening.",
                "source": "maint.txt",
                "min_role": "employee"
            },
            {
                "id": "c2",
                "text": "CRITICAL: Kernel panic incident log_9021 observed on prod-cluster-04.",
                "source": "incidents.txt",
                "min_role": "employee"
            },
            {
                "id": "c3",
                "text": "User onboarding documentation and handbook instructions.",
                "source": "handbook.txt",
                "min_role": "employee"
            }
        ]
        self.bm25_index.add_chunks("it", chunks)

        # Search for exact identifier
        results = self.bm25_index.search("it", "log_9021")
        self.assertTrue(len(results) > 0)
        top_match = results[0]
        self.assertEqual(top_match["id"], "c2")
        self.assertIn("log_9021", top_match["text"])
        self.assertGreater(top_match["lexical_score"], 0.0)

    def test_corpus_bm25_abac_filtering(self):
        """Verifies that ABAC role filtering prevents unauthorized roles from retrieving restricted chunks."""
        chunks = [
            {
                "id": "public_doc",
                "text": "Company holiday schedule for 2025.",
                "metadata": {"source": "holidays.txt", "min_role": "employee"}
            },
            {
                "id": "manager_doc",
                "text": "Confidential managerial performance ratings for 2025.",
                "metadata": {"source": "ratings.txt", "min_role": "manager"}
            },
            {
                "id": "admin_doc",
                "text": "Restricted master root credentials and private keys.",
                "metadata": {"source": "keys.txt", "min_role": "admin"}
            }
        ]
        self.bm25_index.add_chunks("hr", chunks)

        # Employee query
        emp_results = self.bm25_index.search(
            "hr",
            "2025 credentials ratings schedule",
            allowed_roles={"employee", "user"}
        )
        emp_ids = [r["id"] for r in emp_results]
        self.assertIn("public_doc", emp_ids)
        self.assertNotIn("manager_doc", emp_ids)
        self.assertNotIn("admin_doc", emp_ids)

        # Manager query
        mgr_results = self.bm25_index.search(
            "hr",
            "2025 credentials ratings schedule",
            allowed_roles={"manager", "employee", "user"}
        )
        mgr_ids = [r["id"] for r in mgr_results]
        self.assertIn("public_doc", mgr_ids)
        self.assertIn("manager_doc", mgr_ids)
        self.assertNotIn("admin_doc", mgr_ids)

        # Admin query
        admin_results = self.bm25_index.search(
            "hr",
            "2025 credentials ratings schedule",
            allowed_roles={"admin", "manager", "employee", "user"}
        )
        admin_ids = [r["id"] for r in admin_results]
        self.assertIn("public_doc", admin_ids)
        self.assertIn("manager_doc", admin_ids)
        self.assertIn("admin_doc", admin_ids)

    def test_incremental_indexing_and_persistence(self):
        """Verifies that index persists to disk and reloads correctly."""
        chunks_batch1 = [
            {"id": "doc1", "text": "Financial quarterly budget req-4402 report.", "metadata": {"source": "q1.pdf", "min_role": "employee"}}
        ]
        self.bm25_index.add_chunks("finance", chunks_batch1)

        # Create a new index instance pointing to the same disk directory
        reloaded_index = CorpusBM25Index(storage_dir=self.temp_dir)
        results = reloaded_index.search("finance", "req-4402")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "doc1")

        # Delete by source and verify removal
        reloaded_index.delete_by_source("finance", "q1.pdf")
        results_after_delete = reloaded_index.search("finance", "req-4402")
        self.assertEqual(len(results_after_delete), 0)

    def test_reciprocal_rank_fusion(self):
        """Verifies that RRF correctly fuses dense and sparse result sets."""
        dense_results = [
            {"id": "doc_dense_1", "text": "Dense vector top result", "distance": 0.1},
            {"id": "doc_shared", "text": "Shared document across both", "distance": 0.3}
        ]
        sparse_results = [
            {"id": "doc_shared", "text": "Shared document across both", "lexical_score": 5.2},
            {"id": "doc_sparse_1", "text": "Sparse lexical unique result", "lexical_score": 4.1}
        ]

        fused = reciprocal_rank_fusion(dense_results, sparse_results, k=60)
        self.assertEqual(len(fused), 3)
        # Shared document should have the highest combined RRF score
        self.assertEqual(fused[0]["id"], "doc_shared")
        self.assertGreater(fused[0]["rrf_score"], fused[1]["rrf_score"])


class TestDepartmentAgentHybridBM25(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bm25_index = CorpusBM25Index(storage_dir=self.temp_dir)
        
        # Patch the global instance
        import core.hybrid_retriever as hr
        self._orig_instance = hr._corpus_bm25_instance
        hr._corpus_bm25_instance = self.bm25_index

    def tearDown(self):
        import core.hybrid_retriever as hr
        hr._corpus_bm25_instance = self._orig_instance
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_search_exact_text_retrieves_from_corpus_bm25(self):
        """Verifies DepartmentAgent.search_exact_text uses CorpusBM25Index first."""
        self.bm25_index.add_chunks("it", [
            {
                "id": "chunk_log_9021",
                "text": "Incident log_9021 occurred during database failover.",
                "metadata": {"source": "incidents.txt", "min_role": "employee"}
            }
        ])

        agent = DepartmentAgent("it")
        result = agent.search_exact_text("log_9021", user_role="employee")
        self.assertIn("log_9021", result)
        self.assertIn("[Source: incidents.txt]", result)

    def test_hybrid_search_vector_db_finds_sparse_match_when_dense_empty(self):
        """Verifies dual retriever finds documents via CorpusBM25 even when dense search is empty."""
        self.bm25_index.add_chunks("hr", [
            {
                "id": "h1",
                "text": "Parental leave policy guarantees 14 weeks paid leave for secondary caregivers.",
                "metadata": {"source": "parental_leave.txt", "min_role": "employee"}
            }
        ])

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}
        mock_client.get_collection.return_value = mock_collection

        mock_embed = MagicMock()
        mock_embed.encode.return_value.tolist.return_value = [[0.1, 0.2]]

        agent = DepartmentAgent("hr", client=mock_client, embed_model=mock_embed)
        res = agent.search_vector_db("secondary caregivers parental leave", user_role="employee")
        self.assertIn("secondary caregivers", res)
        self.assertIn("14 weeks paid leave", res)


if __name__ == "__main__":
    unittest.main()
