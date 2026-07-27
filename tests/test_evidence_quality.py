import unittest

from agent.evidence_fetcher import FetchResponse, _usable_document


class EvidenceQualityTests(unittest.TestCase):
    def test_rejects_api_error_payload_and_short_pages(self) -> None:
        error = FetchResponse("https://slack.com/api/x", "https://slack.com/api/x", "x", '{"ok":false,"error":"invalid_code"}', "application/json", "test")
        self.assertFalse(_usable_document(error))

    def test_accepts_substantive_developer_document(self) -> None:
        page = FetchResponse("https://docs.example.com/auth", "https://docs.example.com/auth", "Authentication", "OAuth authentication documentation. " * 20, "text/html", "test")
        self.assertTrue(_usable_document(page))


if __name__ == "__main__":
    unittest.main()
