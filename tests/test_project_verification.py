import tempfile
import unittest
from pathlib import Path

from tools.verify import project_markers


class ProjectVerificationTests(unittest.TestCase):
    def test_node_project_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text('{"name":"demo","scripts":{"test":"echo ok"}}')
            result = project_markers(str(root))
            self.assertEqual(result["project_type"], "node")


if __name__ == "__main__":
    unittest.main()
