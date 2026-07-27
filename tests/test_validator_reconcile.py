import copy
import unittest

from agent.reconcile import reconcile_passes
from agent.validator import validate_pass_record


def field(value, citations=("E01",)):
    return {"value": value, "citations": list(citations), "confidence": "supported_primary"}


def valid_record() -> dict:
    return {
        "app_id": "slack",
        "one_liner": field("Messaging platform"),
        "auth_methods": field(["oauth2"]),
        "credential_path": field("self_serve"),
        "gating_reasons": field([]),
        "api_surface": {"protocols": field(["rest"]), "breadth": field("broad"), "documented": field("yes")},
        "mcp": {"official_vendor_mcp": field("no"), "public_mcp_exists": field("unknown", ())},
        "extras": {"webhooks": field("yes"), "sandbox": field("unknown", ()), "api_access_tier": field("free")},
        "viability": {"technical": field("ready"), "blockers": field([])},
    }


class ValidatorAndReconcileTests(unittest.TestCase):
    def test_validator_nulls_uncited_populated_claims(self) -> None:
        record = valid_record()
        record["auth_methods"] = field(["oauth2"], ())
        result = validate_pass_record(record, "slack", {"E01"})
        self.assertFalse(result.is_clean)
        self.assertIsNone(result.record["auth_methods"]["value"])

    def test_validator_nulls_values_outside_the_schema_enum(self) -> None:
        record = valid_record()
        record["mcp"]["official_vendor_mcp"] = field(True)
        result = validate_pass_record(record, "slack", {"E01"})
        self.assertFalse(result.is_clean)
        self.assertIsNone(result.record["mcp"]["official_vendor_mcp"]["value"])

    def test_reconciliation_derives_ready_now_from_supported_inputs(self) -> None:
        first = validate_pass_record(valid_record(), "slack", {"E01"}).record
        second = validate_pass_record(copy.deepcopy(first), "slack", {"E01"}).record
        final = reconcile_passes(first, second, [{"id": "E01", "url": "https://api.slack.com", "excerpt": "OAuth"}])
        self.assertEqual(final["viability"]["combined"]["value"], "ready_now")
        self.assertEqual(final["auth_methods"]["confidence"], "corroborated_primary")

    def test_reconciliation_preserves_conflict_instead_of_picking_a_winner(self) -> None:
        first = validate_pass_record(valid_record(), "slack", {"E01"}).record
        second = validate_pass_record(copy.deepcopy(first), "slack", {"E01"}).record
        second["credential_path"] = field("partner_or_sales_gated", ("E01",))
        final = reconcile_passes(first, second, [])
        self.assertIsNone(final["credential_path"]["value"])
        self.assertEqual(final["credential_path"]["confidence"], "conflicting")


if __name__ == "__main__":
    unittest.main()
