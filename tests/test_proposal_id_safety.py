import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import patches


class ProposalIdSafetyTests(unittest.TestCase):
    def test_load_rejects_traversal_and_malformed_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(patches, "PROPOSALS", Path(temp)):
                self.assertIsNone(patches.load("../../etc/passwd"))
                self.assertIsNone(patches.load("not-a-proposal-id"))

    def test_save_rejects_malformed_id(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(patches, "PROPOSALS", Path(temp)):
                with self.assertRaisesRegex(ValueError, "Invalid proposal ID"):
                    patches.save({"id": "../../outside", "status": "approved"})
                self.assertEqual(list(Path(temp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
