import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


class ApiAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("AGENT_API_TOKEN", None)

    def tearDown(self):
        self.env.stop()

    def test_health_is_public(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_protected_endpoint_fails_closed_when_token_missing(self):
        response = self.client.get("/api/approvals")
        self.assertEqual(response.status_code, 503)
        self.assertIn("AGENT_API_TOKEN is not configured", response.text)

    def test_protected_endpoint_rejects_wrong_token(self):
        with patch.dict(os.environ, {"AGENT_API_TOKEN": "expected-token"}):
            response = self.client.get(
                "/api/approvals", headers={"Authorization": "Bearer wrong-token"}
            )
        self.assertEqual(response.status_code, 401)

    def test_protected_endpoint_accepts_configured_token(self):
        with patch.dict(os.environ, {"AGENT_API_TOKEN": "expected-token"}):
            response = self.client.get(
                "/api/approvals", headers={"Authorization": "Bearer expected-token"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("approvals", response.json())


if __name__ == "__main__":
    unittest.main()
