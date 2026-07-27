import unittest

from agent.evidence_fetcher import FetchError, FetchResponse, HttpFetcher, ResilientFetcher, acquire_hint_evidence
from agent.models import AppSeed
from agent.source_policy import SourcePolicy


class StubFetcher:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def fetch(self, url):
        if self.error:
            raise self.error
        return self.response


class EvidenceFetcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = SourcePolicy.load("data/app_source_policy.json")
        self.seed = AppSeed("slack", "Slack", "Communications", "slack.com")

    def test_acquisition_rejects_non_official_redirect(self) -> None:
        response = FetchResponse("https://slack.com", "https://example.com/post", "Post", "OAuth docs", "text/html", "stub")
        result = acquire_hint_evidence(self.seed, StubFetcher(response), self.policy)
        self.assertIsNone(result.source)
        self.assertIn("Rejected", result.failure)

    def test_primary_failure_uses_fallback(self) -> None:
        response = FetchResponse("https://slack.com", "https://api.slack.com/docs", "Docs", "OAuth docs", "text/html", "fallback")
        fetcher = ResilientFetcher(StubFetcher(error=FetchError("primary unavailable")), StubFetcher(response))
        self.assertEqual(fetcher.fetch("https://slack.com").final_url, "https://api.slack.com/docs")

    def test_malformed_assignment_hint_becomes_fetch_error(self) -> None:
        with self.assertRaises(FetchError):
            HttpFetcher().fetch("paygent (NMI-powered)")


if __name__ == "__main__":
    unittest.main()
