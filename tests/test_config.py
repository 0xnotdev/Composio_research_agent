import os
import unittest
from unittest.mock import patch

from agent.config import Settings


class SettingsTests(unittest.TestCase):
    def test_request_limit_cannot_exceed_free_tier_guardrail(self) -> None:
        with patch.dict(os.environ, {"OPENROUTER_REQUEST_LIMIT": "49"}, clear=True):
            with self.assertRaises(ValueError):
                Settings.from_environment(load_dotenv_file=False)

    def test_empty_environment_is_safe_for_offline_development(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_environment(load_dotenv_file=False)
        self.assertIsNone(settings.composio_api_key)
        self.assertIsNone(settings.openrouter_api_key)
        self.assertEqual(settings.request_limit, 48)


if __name__ == "__main__":
    unittest.main()
