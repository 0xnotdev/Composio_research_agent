import unittest

from agent.analytics import calculate_analytics
from agent.render_case_study import render_case_study


def f(value):
    return {"value": value, "citations": ["E01"], "confidence": "supported_primary"}


class RendererTests(unittest.TestCase):
    def test_html_is_self_contained_and_links_to_official_evidence(self) -> None:
        records = [{"app_id": "slack", "name": "Slack", "category": "Comms", "auth_methods": f(["oauth2"]), "credential_path": f("self_serve"), "api_surface": {"protocols": f(["rest"]), "breadth": f("broad")}, "mcp": {"official_vendor_mcp": f("no"), "public_mcp_exists": f("unknown")}, "viability": {"technical": f("ready"), "combined": f("ready_now"), "blockers": f([])}, "evidence": [{"url": "https://api.slack.com", "excerpt": "OAuth"}]}]
        patterns = [{"headline": "OAuth is common", "insight": "The metrics show OAuth usage.", "caveat": "Small sample."}]
        page = render_case_study(records, calculate_analytics(records), None, "2026-07-27", patterns)
        self.assertIn('href="https://api.slack.com"', page)
        self.assertNotIn('id="dataset"', page)
        self.assertIn("Slack", page)
        self.assertIn("https://api.slack.com", page)
        self.assertIn("How to read blanks and unknowns", page)
        self.assertIn("Agent-generated portfolio patterns", page)
        self.assertIn("OAuth is common", page)
        self.assertNotIn("<link rel=\"stylesheet\"", page)


if __name__ == "__main__":
    unittest.main()
