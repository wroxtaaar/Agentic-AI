import tempfile
from pathlib import Path
import unittest
from tools.safety import sensitive,redact
class SafetyTests(unittest.TestCase):
 def test_env_blocked(self):
  self.assertTrue(sensitive(Path('/tmp/x/.env')))
 def test_redaction(self):
  self.assertIn('[REDACTED]',redact('API_KEY=abc123'))
if __name__=='__main__':unittest.main()
