import os
import unittest
from unittest.mock import Mock, patch

from core.orchestrator import Orchestrator


class ModelRoutingTests(unittest.TestCase):
    def test_legacy_model_is_default_for_both_roles(self):
        env = {
            "OPENROUTER_MODEL": "legacy/model", "OPENROUTER_API_KEY": "test-key",
            "AI_BASE_URL": "https://openrouter.ai/api/v1/chat/completions",
        }
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

    def test_missing_freellmapi_key_has_gateway_specific_error(self):
        env = {
            "AI_BASE_URL": "http://freellmapi:3001/v1/chat/completions",
            "AI_API_KEY": "", "OPENROUTER_API_KEY": "must-not-be-used",
        }
        with patch.dict(os.environ, env, clear=False):
            agent = Orchestrator()
        with self.assertRaisesRegex(RuntimeError, "AI_API_KEY is not configured for the FreeLLMAPI gateway"):
            agent._request("auto", [{"role": "user", "content": "hello"}])

    def test_invalid_json_gateway_response_has_clear_error(self):
        env = {
            "AI_BASE_URL": "http://freellmapi:3001/v1/chat/completions",
            "AI_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env, clear=False):
            agent = Orchestrator()
        response = unittest.mock.Mock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("not json")
        with patch("core.orchestrator.httpx.post", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "AI gateway returned invalid JSON"):
                agent._request("auto", [{"role": "user", "content": "hello"}])

    def test_non_object_gateway_response_has_clear_error(self):
        env = {
            "AI_BASE_URL": "http://freellmapi:3001/v1/chat/completions",
            "AI_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env, clear=False):
            agent = Orchestrator()
        response = unittest.mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = ["unexpected"]
        with patch("core.orchestrator.httpx.post", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "AI gateway returned an unexpected response format"):
                agent._request("auto", [{"role": "user", "content": "hello"}])

    def test_malformed_choice_has_clear_error(self):
        env = {
            "AI_BASE_URL": "http://freellmapi:3001/v1/chat/completions",
            "AI_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env, clear=False):
            agent = Orchestrator()
        response = unittest.mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": ["not-an-object"]}
        with patch("core.orchestrator.httpx.post", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "AI gateway returned no assistant message"):
                agent._request("auto", [{"role": "user", "content": "hello"}])

    def test_valid_tool_calls_always_have_nonempty_ids(self):
        for raw in (
            [{"id": "", "function": {"name": "read_file", "arguments": "{}"}}],
            [{"function": {"name": "read_file", "arguments": "{}"}}],
            [{"id": None, "function": {"name": "read_file", "arguments": "{}"}}],
        ):
            with self.subTest(raw=raw):
                calls, invalid = Orchestrator._valid_tool_calls(raw)
                self.assertEqual(calls, [])
                self.assertEqual(invalid, 1)

    def test_tool_calls_reject_malformed_entries(self):
        calls, invalid = Orchestrator._valid_tool_calls([
            {"id": "good", "function": {"name": "read_file", "arguments": '{"path":"README.md"}'}},
            None,
            {"id": "missing-function", "function": "not-an-object"},
            {"id": "empty-name", "function": {"name": "", "arguments": "{}"}},
            {"id": "bad-arguments", "function": {"name": "read_file", "arguments": {}}},
            {"function": {"name": "read_file", "arguments": "{}"}},
            {"id": "", "function": {"name": "read_file", "arguments": "{}"}},
        ])
        self.assertEqual(len(calls), 1)
        self.assertEqual(invalid, 6)

    def test_tool_calls_reject_non_list_payload(self):
        calls, invalid = Orchestrator._valid_tool_calls({"function": {"name": "read_file"}})
        self.assertEqual(calls, [])
        self.assertEqual(invalid, 1)

    def test_tool_calls_reject_falsey_non_list_payloads(self):
        for raw in ("", 0, False):
            with self.subTest(raw=raw):
                calls, invalid = Orchestrator._valid_tool_calls(raw)
                self.assertEqual(calls, [])
                self.assertEqual(invalid, 1)

    def test_gateway_rejects_non_string_assistant_content(self):
        agent = Orchestrator.__new__(Orchestrator)
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": {"unexpected": "object"}}}]}
        with patch("core.orchestrator.httpx.post", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "malformed assistant content"):
                agent._request("test-model", [{"role": "user", "content": "hello"}])

    def test_gateway_accepts_null_assistant_content_for_tool_calls(self):
        agent = Orchestrator.__new__(Orchestrator)
        agent.api_key = "test-key"
        agent.base_url = "http://freellmapi:3001/v1/chat/completions"
        agent.timeout = 10
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": None, "tool_calls": []}}]}
        with patch("core.orchestrator.httpx.post", return_value=response):
            message = agent._request("test-model", [{"role": "user", "content": "hello"}])
        self.assertIsNone(message["content"])

    def test_tool_result_requires_object(self):
        for raw in (None, [], "ok", 1):
            with self.subTest(raw=raw):
                result = Orchestrator._normalize_tool_result(raw)
                self.assertFalse(result["success"])
                self.assertEqual(result["error_type"], "invalid_tool_result")
                self.assertIn("expected an object", result["error"])

    def test_tool_result_preserves_object(self):
        raw = {"success": True, "value": "ok"}
        self.assertIs(Orchestrator._normalize_tool_result(raw), raw)

    def test_tool_arguments_reject_invalid_json(self):
        args, error = Orchestrator._parse_tool_arguments("{not-json")
        self.assertIsNone(args)
        self.assertIn("invalid JSON", error)

    def test_tool_arguments_require_json_object(self):
        for raw in ("", "[]", '"string"', "null"):
            with self.subTest(raw=raw):
                args, error = Orchestrator._parse_tool_arguments(raw)
                self.assertIsNone(args)
                self.assertIsNotNone(error)

    def test_tool_arguments_accept_json_object(self):
        args, error = Orchestrator._parse_tool_arguments('{"path": "/tmp/project"}')
        self.assertEqual(args, {"path": "/tmp/project"})
        self.assertIsNone(error)

    def test_freellmapi_uses_only_its_gateway_key(self):
        env = {
            "AI_BASE_URL": "http://freellmapi:3001/v1/chat/completions",
            "AI_API_KEY": "freellmapi-key", "OPENROUTER_API_KEY": "openrouter-key",
        }
        with patch.dict(os.environ, env, clear=False):
            agent = Orchestrator()
        self.assertEqual(agent.api_key, "freellmapi-key")

    def test_specialist_model_can_use_separate_chain(self):
        env = {
            "AI_BASE_URL": "http://freellmapi:3001/v1/chat/completions",
            "AI_API_KEY": "test-key",
            "ARCHITECT_MODEL": "auto:reliable",
            "WORKER_MODEL": "auto:coding",
            "SPECIALIST_MODEL": "auto:research",
        }
        with patch.dict(os.environ, env, clear=False):
            agent = Orchestrator()
        self.assertEqual(agent.architect_model, "auto:reliable")
        self.assertEqual(agent.worker_model, "auto:coding")
        self.assertEqual(agent.specialist_model, "auto:research")

    def test_specialist_model_defaults_to_worker_chain(self):
        env = {
            "AI_BASE_URL": "http://freellmapi:3001/v1/chat/completions",
            "AI_API_KEY": "test-key",
            "WORKER_MODEL": "auto:coding",
            "SPECIALIST_MODEL": "",
        }
        with patch.dict(os.environ, env, clear=False):
            agent = Orchestrator()
        self.assertEqual(agent.specialist_model, "auto:coding")

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
