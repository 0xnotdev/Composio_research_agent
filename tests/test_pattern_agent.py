import json
import unittest

from agent.pattern_agent import parse_patterns, synthesize_patterns


class PatternAgentTests(unittest.TestCase):
    def test_parser_requires_exactly_four_grounded_pattern_objects(self) -> None:
        raw = json.dumps({"patterns": [{"headline": f"Pattern {index}", "insight": "Metric-backed observation.", "metric_refs": ["credential_distribution"], "caveat": "Coverage is incomplete."} for index in range(4)]})
        self.assertEqual(len(parse_patterns(raw)), 4)

    def test_synthesis_uses_a_single_constrained_client_call(self) -> None:
        raw = json.dumps({"patterns": [{"headline": f"Pattern {index}", "insight": "Metric-backed observation.", "metric_refs": ["credential_distribution"], "caveat": "Coverage is incomplete."} for index in range(4)]})

        class FakeClient:
            def complete(self, **kwargs):
                self.kwargs = kwargs
                return raw

        client = FakeClient()
        result = synthesize_patterns(client, {"record_count": 100})
        self.assertEqual(len(result), 4)
        self.assertEqual(client.kwargs["purpose"], "portfolio_pattern_synthesis")
