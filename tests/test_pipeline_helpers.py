import json
import tempfile
import unittest

from agent.evidence_fetcher import FetchResponse
from agent.models import AppSeed
from agent.pipeline import ResearchPipeline, chunks
from agent.source_policy import SourcePolicy
from agent.storage import RunStore


class PipelineHelperTests(unittest.TestCase):
    def test_batches_never_exceed_six_apps(self) -> None:
        apps = [AppSeed(str(index), str(index), "A", "example.com") for index in range(13)]
        result = list(chunks(apps))
        self.assertEqual([len(batch) for batch in result], [8, 5])

    def test_offline_fixture_run_persists_reconciled_dataset(self) -> None:
        def field(value, citations=("E01",)):
            return {"value": value, "citations": list(citations), "confidence": "supported_primary"}

        record = {
            "app_id": "slack", "one_liner": field("Messaging API"), "auth_methods": field(["oauth2"]), "credential_path": field("self_serve"), "gating_reasons": field([]),
            "api_surface": {"protocols": field(["rest"]), "breadth": field("broad"), "documented": field("yes")},
            "mcp": {"official_vendor_mcp": field("no"), "public_mcp_exists": field("unknown", ())},
            "extras": {"webhooks": field("yes"), "sandbox": field("unknown", ()), "api_access_tier": field("free")},
            "viability": {"technical": field("ready"), "blockers": field([])},
        }

        class FakeFetcher:
            def fetch(self, url):
                return FetchResponse(url, "https://api.slack.com/docs", "Slack API", "OAuth authentication lets developers create an application and access the REST API. Webhooks notify applications about events.", "text/html", "fixture")

        class FakeClient:
            def complete(self, **kwargs):
                return json.dumps(record)

        with tempfile.TemporaryDirectory() as directory:
            pipeline = ResearchPipeline(RunStore(directory, "fixture"), SourcePolicy.load("data/app_source_policy.json"), FakeFetcher(), FakeClient(), 48)
            final = pipeline.run([AppSeed("slack", "Slack", "Communications", "slack.com")])
            self.assertEqual(final[0]["viability"]["combined"]["value"], "ready_now")
            self.assertEqual(pipeline.store.read_json("dataset_final.json")[0]["name"], "Slack")


if __name__ == "__main__":
    unittest.main()
