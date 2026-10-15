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
