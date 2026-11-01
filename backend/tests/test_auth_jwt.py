"""
Integration tests for Zero-Trust OAuth2 JWT Bearer authentication & password hashing.
Verifies token issuance, cryptographic verification, tampering rejection, and expiration.
"""

import time
import unittest
from core.schemas import User
from core.security import (
    hash_password, verify_password,
    create_jwt, decode_jwt,
    create_access_token, create_refresh_token
)

class TestAuthJWTIntegration(unittest.TestCase):

    def setUp(self):
        self.user = User(
            username="analyst_alice",
            role="employee",
            status="active",
            allowed_departments=["finance", "it"]
        )

    def test_password_hash_and_verify(self):
        password = "P@ssword_With_Entropy_2026!"
        hashed = hash_password(password)
        self.assertTrue(hashed.startswith("$pbkdf2-sha256$600000$"))
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword123", hashed))
        self.assertFalse(verify_password("", hashed))

    def test_jwt_issuance_and_decoding(self):
        token = create_access_token(self.user)
        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split(".")), 3)

        payload = decode_jwt(token)
        self.assertEqual(payload["sub"], "analyst_alice")
        self.assertEqual(payload["role"], "employee")
        self.assertEqual(payload["allowed_departments"], ["finance", "it"])
        self.assertEqual(payload["scope"], "access")
        self.assertGreater(payload["exp"], time.time())

    def test_refresh_token_scope(self):
        refresh_token = create_refresh_token(self.user)
        payload = decode_jwt(refresh_token)
        self.assertEqual(payload["sub"], "analyst_alice")
        self.assertEqual(payload["scope"], "refresh")

    def test_tampered_jwt_signature_rejection(self):
        token = create_access_token(self.user)
        header_b64, payload_b64, sig_b64 = token.split(".")

        # Tamper with the payload (escalating role to admin)
        import base64
        import json
        padding = 4 - (len(payload_b64) % 4)
        padded = payload_b64 + ("=" * (padding % 4))
        raw_payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        raw_payload["role"] = "admin"
        tampered_payload_b64 = base64.urlsafe_b64encode(json.dumps(raw_payload).encode("utf-8")).decode("utf-8").rstrip("=")

        tampered_token = f"{header_b64}.{tampered_payload_b64}.{sig_b64}"
        with self.assertRaises(ValueError) as ctx:
            decode_jwt(tampered_token)
        self.assertIn("signature mismatch", str(ctx.exception).lower())

    def test_expired_jwt_rejection(self):
        # Create token that expired 10 seconds ago
        expired_token = create_jwt({"sub": "bob", "role": "employee"}, expires_seconds=-10)
        with self.assertRaises(ValueError) as ctx:
            decode_jwt(expired_token)
        self.assertIn("expired", str(ctx.exception).lower())

if __name__ == "__main__":
    unittest.main()
