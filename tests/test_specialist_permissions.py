import unittest
from unittest.mock import patch

from core.orchestrator import Orchestrator, SPECIALIST_READONLY_TOOL_NAMES


class SpecialistToolPermissionTests(unittest.TestCase):
    def setUp(self):
        self.tools = {
            "read_file": {"function": lambda **kwargs: {"success": True}},
            "coding_write_file": {"function": lambda **kwargs: {"success": True}},
            "git_commit": {"function": lambda **kwargs: {"success": True}},
        }
        self.readonly_names = SPECIALIST_READONLY_TOOL_NAMES

    def test_run_marks_empty_worker_response_as_unverified(self):
        agent = Orchestrator()
        with patch.object(agent, "_direct_read_only_git", return_value=None), \
             patch.object(agent, "specialists", return_value=["project"]), \
             patch.object(agent, "_architect_plan", return_value=("plan", None)), \
             patch.object(agent, "_specialist_investigations", return_value=[]), \
             patch.object(agent, "_request", return_value={"content": "  "} ), \
             patch.object(agent, "_architect_review") as review:
            result = agent.run("Investigate the project")

        self.assertFalse(result["success"])
        self.assertIn("completion is unverified", result["answer"])
        self.assertIn("Skipped", result["architect_review"])
        review.assert_not_called()

    def test_worker_request_failure_preserves_specialist_evidence(self):
        agent = Orchestrator()
        reports = [{"agent": "project", "success": True, "report": "Found project files."}]
        with patch.object(agent, "_direct_read_only_git", return_value=None), \
             patch.object(agent, "specialists", return_value=["project"]), \
             patch.object(agent, "_architect_plan", return_value=("plan", None)), \
             patch.object(agent, "_specialist_investigations", return_value=reports), \
             patch.object(agent, "_request", side_effect=RuntimeError("provider rate limited")):
            result = agent.run("Investigate the project")

        self.assertFalse(result["success"])
        self.assertIn("provider rate limited", result["answer"])
        self.assertEqual(result["specialist_reports"], reports)
        self.assertEqual(result["architect_plan"], "plan")
        self.assertEqual(result["worker_model"], agent.worker_model)
        self.assertIn("Skipped", result["architect_review"])

    def test_empty_worker_response_is_not_usable(self):
        self.assertFalse(Orchestrator._worker_response_is_usable(""))
        self.assertFalse(Orchestrator._worker_response_is_usable("  \n"))

    def test_nonempty_worker_response_is_usable(self):
        self.assertTrue(Orchestrator._worker_response_is_usable("Task report"))

    def test_empty_specialist_report_is_unavailable(self):
        report = Orchestrator._build_specialist_report("security", "  ", [], 0)
        self.assertFalse(report["success"])
        self.assertIn("unavailable", report["report"])
        self.assertEqual(report["agent"], "security")
        self.assertEqual(report["tool_calls"], 0)

    def test_nonempty_specialist_report_is_successful(self):
        report = Orchestrator._build_specialist_report(
            "verifier", "Tests were checked.", [{"tool": "verify_project", "success": True}], 1
        )
        self.assertTrue(report["success"])
        self.assertEqual(report["report"], "Tests were checked.")
        self.assertEqual(report["tool_calls"], 1)
        self.assertEqual(report["tool_trace"][0]["tool"], "verify_project")

    def test_explicit_read_only_role_tool_is_allowed(self):
        self.assertTrue(
            Orchestrator._specialist_tool_is_allowed(
                "read_file", {"read_file"}, self.readonly_names, self.tools
            )
        )

    def test_mutation_tool_is_denied_even_if_model_requests_it(self):
        self.assertFalse(
            Orchestrator._specialist_tool_is_allowed(
                "coding_write_file",
                {"coding_write_file"},
                self.readonly_names,
                self.tools,
            )
        )

    def test_proposal_or_mutation_tool_is_denied_even_if_added_to_role_allowlist(self):
        self.assertFalse(
            Orchestrator._specialist_tool_is_allowed(
                "git_commit",
                {"git_commit"},
                self.readonly_names,
                self.tools,
            )
        )

    def test_read_only_tool_not_in_role_allowlist_is_denied(self):
        self.assertFalse(
            Orchestrator._specialist_tool_is_allowed(
                "git_status", {"read_file"}, self.readonly_names, self.tools
            )
        )

    def test_unregistered_tool_is_denied(self):
        self.assertFalse(
            Orchestrator._specialist_tool_is_allowed(
                "unknown_tool", {"unknown_tool"}, self.readonly_names, self.tools
            )
        )


if __name__ == "__main__":
    unittest.main()
