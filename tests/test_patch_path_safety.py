import tempfile
import unittest
from pathlib import Path

from tools.patches import _safe_target


class PatchPathSafetyTests(unittest.TestCase):
    def test_rejects_absolute_and_traversal_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            self.assertIsNone(_safe_target(root, "/etc/passwd"))
            self.assertIsNone(_safe_target(root, "../outside.txt"))
            self.assertIsNone(_safe_target(root, ""))

    def test_rejects_symlink_that_resolves_outside_project(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "project"
            root.mkdir()
            outside = base / "outside.txt"
            outside.write_text("do not modify", encoding="utf-8")
            (root / "link.txt").symlink_to(outside)
            self.assertIsNone(_safe_target(root.resolve(), "link.txt"))
            self.assertEqual(outside.read_text(encoding="utf-8"), "do not modify")

    def test_rejects_sensitive_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            secret = root / ".env"
            secret.write_text("TOKEN=hidden", encoding="utf-8")
            self.assertIsNone(_safe_target(root, ".env"))

    def test_accepts_normal_relative_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            target = root / "app.py"
            target.write_text("print('ok')", encoding="utf-8")
            self.assertEqual(_safe_target(root, "app.py"), target)


if __name__ == "__main__":
    unittest.main()
