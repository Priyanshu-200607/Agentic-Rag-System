"""
Integration tests for Persistent Administrative Sudo Barrier (Hexagonal State).
Simulates multi-worker process concurrency, cryptographic MAC signatures, and timeout bounds.
"""

import os
import time
import tempfile
import unittest
from infrastructure.state.sqlite_state import SQLiteStateProvider
from core.security import generate_sudo_token, verify_sudo_token

class TestSudoBarrierIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_state.db")
        # Worker 1 connection
        self.worker1_state = SQLiteStateProvider(db_path=self.db_path)
        # Worker 2 connection (separate process / connection simulation)
        self.worker2_state = SQLiteStateProvider(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_persistent_sudo_across_workers(self):
        username = "admin"
        client_ip = "192.168.1.100"

        # Worker 1 issues the elevated sudo token
        sudo_token = generate_sudo_token(username, client_ip=client_ip, state=self.worker1_state)
        self.assertTrue(len(sudo_token) >= 32)

        # Worker 2 verifies the sudo token against shared SQLite WAL store
        self.assertTrue(
            verify_sudo_token(sudo_token, username=username, client_ip=client_ip, state=self.worker2_state),
            "Worker 2 must successfully verify a sudo token issued by Worker 1"
        )

    def test_sudo_ip_binding_protection(self):
        username = "admin"
        legit_ip = "10.0.0.5"
        spoofed_ip = "10.0.0.99"

        sudo_token = generate_sudo_token(username, client_ip=legit_ip, state=self.worker1_state)

        # Verification with spoofed client IP must fail
        self.assertFalse(
            verify_sudo_token(sudo_token, username=username, client_ip=spoofed_ip, state=self.worker2_state)
        )

    def test_sudo_username_binding_protection(self):
        legit_user = "admin"
        attacker = "malicious_user"
        ip = "10.0.0.5"

        sudo_token = generate_sudo_token(legit_user, client_ip=ip, state=self.worker1_state)

        # Verification with different username must fail
        self.assertFalse(
            verify_sudo_token(sudo_token, username=attacker, client_ip=ip, state=self.worker2_state)
        )

    def test_sudo_token_expired(self):
        username = "admin"
        ip = "127.0.0.1"

        sudo_token = generate_sudo_token(username, client_ip=ip, state=self.worker1_state)

        # Fast-forward token expiration in DB
        with self.worker1_state._get_connection() as conn:
            conn.execute("UPDATE sudo_sessions SET expires_at = ? WHERE token = ?", (time.time() - 5, sudo_token))

        # Verification must fail and purge expired token
        self.assertFalse(
            verify_sudo_token(sudo_token, username=username, client_ip=ip, state=self.worker2_state)
        )
        self.assertIsNone(self.worker2_state.get_sudo_session(sudo_token))

if __name__ == "__main__":
    unittest.main()
