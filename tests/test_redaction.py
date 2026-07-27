import unittest

from agent.redaction import redact


class RedactionTests(unittest.TestCase):
    def test_known_secret_is_redacted_from_diagnostics(self) -> None:
        secret = "sensitive-value"
        self.assertEqual(redact(f"request failed with {secret}", (secret,)), "request failed with [REDACTED]")


if __name__ == "__main__":
    unittest.main()
