import os
import tempfile
import unittest
from pathlib import Path

os.environ["AGENT_APPROVAL_DB"] = str(Path(tempfile.gettempdir()) / "agentic-ai-test-approvals.json")

from core.approvals import create, get, set_status
from tools.shell import run_command


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        Path(os.environ["AGENT_APPROVAL_DB"]).unlink(missing_ok=True)

    def test_approval_lifecycle(self):
        item = create("docker_restart", "test", {"container": "demo"})
        self.assertEqual(item["status"], "pending")
        self.assertEqual(set_status(item["id"], "approved")["status"], "approved")
        self.assertEqual(get(item["id"])["status"], "approved")
        self.assertEqual(set_status(item["id"], "executed")["status"], "executed")

    def test_invalid_status_rejected(self):
        item = create("test", "test", {})
        with self.assertRaises(ValueError):
            set_status(item["id"], "bogus")


class ShellSafetyTests(unittest.TestCase):
    def test_redirection_is_blocked(self):
        result = run_command("ls /home/ubuntu > /tmp/out")
        self.assertFalse(result["success"])

    def test_non_workspace_path_is_blocked(self):
        result = run_command("ls /etc")
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
