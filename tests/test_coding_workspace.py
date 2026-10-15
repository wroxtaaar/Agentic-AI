import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import coding_workspace as cw


class CodingWorkspaceSafetyTests(unittest.TestCase):
    def test_rejects_paths_outside_configured_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(cw, "roots", return_value=[Path("/definitely/not/a/root")]):
                result = cw.create_workspace(temp)
        self.assertFalse(result["success"])
        self.assertIn("outside configured", result["error"])

    def test_rejects_path_traversal_in_workspace_file(self):
        result = cw.read_workspace_file("../../etc/passwd", "../secret")
        self.assertFalse(result["success"])

    def test_sensitive_files_are_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".env").write_text("TOKEN=secret")
            item = {"id": "a" * 16, "project": str(root), "worktree": str(root), "status": "editing"}
            with patch.object(cw, "_load", return_value=item):
                result = cw.read_workspace_file("a" * 16, ".env")
        self.assertFalse(result["success"])
        self.assertIn("blocked", result["error"])


if __name__ == "__main__":
    unittest.main()
