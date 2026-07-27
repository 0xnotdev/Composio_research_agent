import unittest

from agent.analytics import calculate_analytics
from agent.verification import score_verification_sample, select_verification_sample


def f(value, confidence="supported_primary"):
    return {"value": value, "citations": ["E01"], "confidence": confidence}


def record(app_id, category, credential="self_serve", mcp="no"):
    return {
        "app_id": app_id,
        "name": app_id.title(),
        "category": category,
        "auth_methods": f(["oauth2"]),
        "credential_path": f(credential),
        "api_surface": {"protocols": f(["rest"]), "breadth": f("broad")},
        "mcp": {"official_vendor_mcp": f(mcp)},
        "viability": {"technical": f("ready"), "combined": f("ready_now"), "blockers": f([])},
        "audit": {"researcher_pass1": {"auth_methods": f(["oauth2"]), "credential_path": f(credential), "api_surface": {"protocols": f(["rest"]), "breadth": f("broad")}, "mcp": {"official_vendor_mcp": f(mcp)}, "viability": {"technical": f("ready")}}},
    }


class AnalyticsAndVerificationTests(unittest.TestCase):
    def test_easy_wins_and_distributions_are_calculated_from_records(self) -> None:
        records = [record("alpha", "A"), record("beta", "B", credential="partner_or_sales_gated")]
        analysis = calculate_analytics(records)
        self.assertEqual(analysis["record_count"], 2)
        self.assertEqual(analysis["distributions"]["credential_path"]["self_serve"], 1)
        self.assertEqual([item["app_id"] for item in analysis["easy_wins"]], ["alpha"])
        self.assertEqual([item["app_id"] for item in analysis["outreach_candidates"]], ["beta"])

    def test_sample_is_stratified_and_accuracy_is_not_inferred(self) -> None:
        records = [record("alpha", "A"), record("beta", "B")]
        sample = select_verification_sample(records)
        self.assertEqual(len(sample), 2)
        for item in sample:
            for judgement in item["judgements"]:
                judgement.update({"ground_truth": judgement["final_pre_human_value"], "pass1_correct": True, "final_pre_human_correct": True})
        result = score_verification_sample(sample)
        self.assertEqual(result["pass1_accuracy_percent"], 100.0)
        self.assertEqual(result["final_pre_human_accuracy_percent"], 100.0)

    def test_category_representative_prefers_supported_answers(self) -> None:
        weak = record("weak", "A")
        for path in ("auth_methods", "credential_path"):
            weak[path] = {"value": None, "citations": [], "confidence": "insufficient_evidence"}
        strong = record("strong", "A")
        sample = select_verification_sample([weak, strong])
        self.assertEqual(sample[0]["app_id"], "strong")


if __name__ == "__main__":
    unittest.main()
