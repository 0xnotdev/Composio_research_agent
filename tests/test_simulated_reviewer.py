import json
import unittest

from agent.simulated_reviewer import simulate


class SimulatedReviewerTests(unittest.TestCase):
    def test_result_is_explicitly_not_human_validation(self) -> None:
        sample = [{"app_id": "alpha", "judgements": [{"path": "auth_methods", "pass1_value": ["oauth2"], "final_pre_human_value": ["oauth2"]}]}]
        records = [{"app_id": "alpha", "evidence": [{"url": "https://official.example", "excerpt": "OAuth documentation"}]}]

        class FakeClient:
            def complete(self, **kwargs):
                return json.dumps({"reviews": [{"app_id": "alpha", "judgements": [{"path": "auth_methods", "ground_truth": "oauth2", "reason": "Supported."}]}]})

        result = simulate(FakeClient(), sample, records)
        self.assertEqual(result["mode"], "ai_simulated_reviewer_not_human_validation")
        self.assertEqual(result["judged_fields"], 1)
        self.assertEqual(result["final_pre_human_accuracy_percent"], 100.0)
