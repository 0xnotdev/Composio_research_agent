import json
import unittest

from agent.evidence_packer import build_evidence_pack
from agent.models import AppSeed, EvidenceSource
from agent.researcher import build_researcher_user_prompt


class PromptIsolationTests(unittest.TestCase):
    def test_batch_prompt_keeps_same_local_source_id_with_its_own_app(self) -> None:
        apps = [AppSeed("alpha", "Alpha", "A", "alpha.com"), AppSeed("beta", "Beta", "B", "beta.com")]
        alpha = EvidenceSource("S01", "https://alpha.com/docs", "Alpha", "official_docs", "2026-07-27T00:00:00Z", "OAuth authentication is supported for Alpha API, and developers can create an application to receive access credentials.")
        beta = EvidenceSource("S01", "https://beta.com/docs", "Beta", "official_docs", "2026-07-27T00:00:00Z", "OAuth authentication is supported for Beta API, and developers can create an application to receive access credentials.")
        payload = json.loads(build_researcher_user_prompt(apps, {"alpha": build_evidence_pack([alpha]), "beta": build_evidence_pack([beta])}, {"alpha": {"S01": alpha}, "beta": {"S01": beta}}))
        self.assertEqual(payload["apps"][0]["evidence"][0]["url"], "https://alpha.com/docs")
        self.assertEqual(payload["apps"][1]["evidence"][0]["url"], "https://beta.com/docs")


if __name__ == "__main__":
    unittest.main()
