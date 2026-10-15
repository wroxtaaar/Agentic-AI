import unittest

from core.orchestrator import Orchestrator, SPECIALIST_READONLY_TOOL_NAMES


class SpecialistToolPermissionTests(unittest.TestCase):
    def setUp(self):
        self.tools = {
            "read_file": {"function": lambda **kwargs: {"success": True}},
            "coding_write_file": {"function": lambda **kwargs: {"success": True}},
            "git_commit": {"function": lambda **kwargs: {"success": True}},
        }
        self.readonly_names = SPECIALIST_READONLY_TOOL_NAMES

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
