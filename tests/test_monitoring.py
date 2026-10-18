import unittest

from monitoring.worker import fingerprint, redact


class MonitoringSafetyTests(unittest.TestCase):
    def test_redacts_bearer_token(self):
        value = redact("Authorization: Bearer abcdefghijklmnop")
        self.assertIn("[REDACTED]", value)
        self.assertNotIn("abcdefghijklmnop", value)

    def test_redacts_password_assignment(self):
        value = redact("password=super-secret-value")
        self.assertIn("[REDACTED]", value)
        self.assertNotIn("super-secret-value", value)

    def test_fingerprint_ignores_timestamps(self):
        first = fingerprint("service", "2026-10-14T10:00:00Z ERROR request failed")
        second = fingerprint("service", "2026-10-14T10:05:00Z ERROR request failed")
        self.assertEqual(first, second)

    def test_fingerprint_ignores_long_hex_ids(self):
        first = fingerprint("service", "request abcdef0123456789abcdef0123456789 failed")
        second = fingerprint("service", "request 1234567890abcdef1234567890abcdef failed")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
