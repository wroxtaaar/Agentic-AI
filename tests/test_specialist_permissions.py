import unittest

from core.orchestrator import Orchestrator


class SpecialistToolPermissionTests(unittest.TestCase):
    def setUp(self):
        self.tools = {
            "read_file": {"function": lambda **kwargs: {"success": True}},
            "coding_write_file": {"function": lambda **kwargs: {"success": True}},
        }
        self.readonly_names = {"read_file", "git_status", "verify_project"}

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
