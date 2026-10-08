import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.audit import audit_project
from tools.projects import read_files
from tools.verify import project_markers


class ProjectVerificationTests(unittest.TestCase):
    def test_node_project_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text('{"name":"demo","scripts":{"test":"echo ok"}}')
            result = project_markers(str(root))
            self.assertEqual(result["project_type"], "node")

    def test_audit_reports_git_failure_without_inventing_missing_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            (root / "build.gradle.kts").write_text("plugins {}")
            with patch("tools.audit.roots", return_value=[root]):
                result = audit_project(str(root))
            self.assertTrue(result["success"])
            self.assertIn("git", result)
            self.assertIsNone(result["git"]["dirty"])
            self.assertTrue(any(x["title"] == "Git state could not be fully verified" for x in result["findings"]))

    def test_batch_read_returns_multiple_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.txt"
            b = root / "b.txt"
            a.write_text("alpha")
            b.write_text("beta")
            # The test helper uses the configured workspace, so this validates
            # the API shape independently of deployment configuration.
            with patch("tools.projects.roots", return_value=[root]):
                result = read_files([str(a), str(b)])
            self.assertTrue(result["success"])
            self.assertEqual([x["content"] for x in result["files"]], ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
