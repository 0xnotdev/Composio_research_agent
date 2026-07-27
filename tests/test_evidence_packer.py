import unittest

from agent.evidence_packer import build_evidence_pack, html_to_text
from agent.models import EvidenceSource


class EvidencePackerTests(unittest.TestCase):
    def test_html_cleaning_drops_scripts_and_keeps_research_content(self) -> None:
        text = html_to_text("<h1>API docs</h1><script>secrets()</script><p>OAuth authentication uses access tokens.</p>")
        self.assertIn("OAuth authentication", text)
        self.assertNotIn("secrets", text)

    def test_pack_is_bounded_and_citation_ready(self) -> None:
        source = EvidenceSource(
            source_id="S01",
            url="https://api.example.com/docs",
            title="Authentication",
            source_type="official_docs",
            retrieved_at="2026-07-27T00:00:00Z",
            text=(
                "OAuth 2.0 authentication is supported for developer applications. "
                "Create an app in the developer portal to obtain credentials.\n\n"
                "The REST API provides endpoints for users, records, and events. "
                "Webhooks can notify applications about updates."
            ),
        )
        pack = build_evidence_pack([source], max_characters=240)
        self.assertGreaterEqual(len(pack.excerpts), 1)
        self.assertLessEqual(sum(len(item.text) for item in pack.excerpts), 240)
        self.assertEqual(pack.excerpts[0].excerpt_id, "E01")
        self.assertIn("auth", pack.excerpts[0].dimensions)


if __name__ == "__main__":
    unittest.main()
