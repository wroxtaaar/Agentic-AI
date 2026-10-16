import os
import unittest
from unittest.mock import patch

from core.orchestrator import Orchestrator


class SpecialistAgentTests(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {
            "AI_BASE_URL": "http://freellmapi:3001/v1/chat/completions",
            "AI_API_KEY": "test-key",
            "MAX_SPECIALIST_AGENTS": "3",
            "SPECIALIST_MAX_TURNS": "3",
        }, clear=False):
            self.agent = Orchestrator()

    def test_specialist_can_use_allowlisted_read_only_tool(self):
        calls = []
        self.agent.tools = {
            "git_status": {
                "name": "git_status",
                "description": "Read Git status",
                "schema": {"type": "object", "properties": {}, "required": []},
                "function": lambda: calls.append("git_status") or {"success": True, "branch": "main"},
            }
        }
        responses = [
            {
                "tool_calls": [{
                    "id": "call-1",
                    "function": {"name": "git_status", "arguments": "{}"},
                }]
            },
            {"content": "Evidence: Git status returned branch main."},
        ]
        with patch.object(self.agent, "_request", side_effect=responses):
            reports = self.agent._specialist_investigations("Check Git", "Inspect status", ["git"])
        self.assertEqual(calls, ["git_status"])
        self.assertEqual(len(reports), 1)
        self.assertTrue(reports[0]["success"])
        self.assertEqual(reports[0]["tool_calls"], 1)
        self.assertEqual(reports[0]["tool_trace"][0]["tool"], "git_status")

    def test_specialist_rejects_empty_tool_arguments(self):
        calls = []
        self.agent.tools = {
            "git_status": {
                "name": "git_status",
                "description": "Read Git status",
                "schema": {"type": "object", "properties": {}, "required": []},
                "function": lambda: calls.append("git_status") or {"success": True},
            }
        }
        responses = [
            {"tool_calls": [{
                "id": "call-empty",
                "function": {"name": "git_status", "arguments": ""},
            }]},
            {"content": "I could not inspect Git status because the tool arguments were malformed."},
        ]
        with patch.object(self.agent, "_request", side_effect=responses):
            reports = self.agent._specialist_investigations("Check Git", "Inspect status", ["git"])
        self.assertEqual(calls, [])
        self.assertFalse(reports[0]["success"])
        self.assertIn("INCOMPLETE", reports[0]["report"])
        self.assertFalse(reports[0]["tool_trace"][0]["success"])
        self.assertIn("non-empty JSON object", reports[0]["tool_trace"][0]["error"])

    def test_specialist_cannot_execute_mutating_tool(self):
        calls = []
        self.agent.tools = {
            "docker_restart": {
                "name": "docker_restart",
                "description": "Mutating action",
                "schema": {"type": "object", "properties": {}, "required": []},
                "function": lambda: calls.append("docker_restart") or {"success": True},
            }
        }
        responses = [
            {
                "tool_calls": [{
                    "id": "call-1",
                    "function": {"name": "docker_restart", "arguments": "{}"},
                }]
            },
            {"content": "The requested mutation was blocked by the specialist tool policy."},
        ]
        with patch.object(self.agent, "_request", side_effect=responses):
            reports = self.agent._specialist_investigations("Restart service", "Inspect safely", ["devops"])
        self.assertEqual(calls, [])
        self.assertFalse(reports[0]["tool_trace"][0]["success"])
        self.assertIn("not permitted", reports[0]["tool_trace"][0]["error"])

    def test_specialist_agent_count_is_bounded(self):
        with patch.dict(os.environ, {"MAX_SPECIALIST_AGENTS": "99"}, clear=False):
            with patch.object(self.agent, "_request", return_value={"content": "Reviewed."}) as request:
                reports = self.agent._specialist_investigations(
                    "Check all", "Plan", ["project", "coding", "devops", "git", "security"]
                )
        self.assertEqual(len(reports), 5)
        self.assertEqual(request.call_count, 5)


if __name__ == "__main__":
    unittest.main()
