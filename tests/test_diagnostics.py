import unittest
from unittest.mock import patch
from tools import diagnostics


class DiagnosticsTests(unittest.TestCase):
    @patch("tools.diagnostics.subprocess.run")
    def test_logs_are_bounded_and_redacted(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "Authorization: Bearer abcdefghijklmnop\npassword=hunter2\n"
        run.return_value.stderr = ""
        result = diagnostics.container_logs("agentic-ai", 9999)
        self.assertTrue(result["success"])
        self.assertEqual(result["lines_requested"], diagnostics.MAX_LOG_LINES)
        self.assertIn("[REDACTED]", result["logs"])
        self.assertNotIn("abcdefghijklmnop", result["logs"])
        self.assertNotIn("hunter2", result["logs"])
        args = run.call_args.args[0]
        self.assertEqual(args[:4], ["docker", "logs", "--timestamps", "--tail"])
        self.assertEqual(args[-1], "agentic-ai")

    def test_arbitrary_container_is_rejected(self):
        with self.assertRaises(ValueError):
            diagnostics.container_logs("agentic-ai; rm -rf /", 10)
        with self.assertRaises(ValueError):
            diagnostics.container_diagnostics("some-other-container")

    @patch("tools.diagnostics.subprocess.run")
    def test_container_status_is_parsed(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "/agentic-ai|running|healthy|3"
        run.return_value.stderr = ""
        result = diagnostics.list_diagnostics_containers()
        item = next(x for x in result["containers"] if x["name"] == "agentic-ai")
        self.assertTrue(item["available"])
        self.assertEqual(item["status"], "running")
        self.assertEqual(item["health"], "healthy")
        self.assertEqual(item["restart_count"], 3)


if __name__ == "__main__":
    unittest.main()
