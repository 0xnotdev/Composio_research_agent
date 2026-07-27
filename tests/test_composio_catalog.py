import unittest

from agent.composio_catalog import cross_check


class CatalogCrossCheckTests(unittest.TestCase):
    def test_matching_is_conservative_and_secondary(self) -> None:
        records = [{"app_id": "slack", "name": "Slack"}, {"app_id": "unknown_app", "name": "Unknown App"}]
        checked = cross_check(records, [{"slug": "slack", "name": "Slack", "toolCount": 12}])
        self.assertEqual(checked[0]["composio_cross_check"]["match_status"], "matched")
        self.assertEqual(checked[0]["composio_cross_check"]["tool_count"], 12)
        self.assertEqual(checked[1]["composio_cross_check"]["match_status"], "no_confident_match")


if __name__ == "__main__":
    unittest.main()
