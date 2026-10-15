import os
import unittest
from unittest.mock import patch

from core.orchestrator import Orchestrator


class ModelRoutingTests(unittest.TestCase):
    def test_legacy_model_is_default_for_both_roles(self):
        env = {"OPENROUTER_MODEL": "legacy/model", "OPENROUTER_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=False):
            with patch.dict(os.environ, {"ARCHITECT_MODEL": "", "WORKER_MODEL": ""}, clear=False):
                agent = Orchestrator()
        self.assertEqual(agent.architect_model, "legacy/model")
        self.assertEqual(agent.worker_model, "legacy/model")

    def test_architect_and_worker_models_can_differ(self):
        env = {
            "OPENROUTER_MODEL": "legacy/model", "ARCHITECT_MODEL": "architect/model",
            "WORKER_MODEL": "worker/model", "OPENROUTER_API_KEY": "test-key",
            "AI_BASE_URL": "http://127.0.0.1:8080/v1/chat/completions",
        }
        with patch.dict(os.environ, env, clear=False):
            agent = Orchestrator()
        self.assertEqual(agent.architect_model, "architect/model")
        self.assertEqual(agent.worker_model, "worker/model")
        self.assertEqual(agent.base_url, env["AI_BASE_URL"])

    def test_freellmapi_does_not_fall_back_to_openrouter_key(self):
        env = {
            "AI_BASE_URL": "http://freellmapi:3001/v1/chat/completions",
            "AI_API_KEY": "", "OPENROUTER_API_KEY": "should-not-be-used",
            "ARCHITECT_MODEL": "", "WORKER_MODEL": "",
        }
        with patch.dict(os.environ, env, clear=False):
            agent = Orchestrator()
        self.assertIsNone(agent.api_key)
        self.assertEqual(agent.architect_model, "auto")
        self.assertEqual(agent.worker_model, "auto")

    def test_freellmapi_uses_only_its_gateway_key(self):
        env = {
            "AI_BASE_URL": "http://freellmapi:3001/v1/chat/completions",
            "AI_API_KEY": "freellmapi-key", "OPENROUTER_API_KEY": "openrouter-key",
        }
        with patch.dict(os.environ, env, clear=False):
            agent = Orchestrator()
        self.assertEqual(agent.api_key, "freellmapi-key")

    def test_planning_failure_is_reported_and_falls_back(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False):
            agent = Orchestrator()
        with patch.object(agent, "_request", side_effect=RuntimeError("gateway offline")):
            plan, error = agent._architect_plan("Fix tests", [], ["coding"])
        self.assertIn("planning unavailable", plan)
        self.assertIn("gateway offline", error)

    def test_review_failure_is_reported(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False):
            agent = Orchestrator()
        with patch.object(agent, "_request", side_effect=RuntimeError("offline")):
            review, error = agent._architect_review("task", "plan", "report")
        self.assertIn("without independent review", review)
        self.assertIn("offline", error)


if __name__ == "__main__":
    unittest.main()
