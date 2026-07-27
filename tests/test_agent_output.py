import unittest

from agent.agent_output import AgentOutputError, parse_ordered_jsonl


class AgentOutputTests(unittest.TestCase):
    def test_parser_requires_order_and_one_row_per_app(self) -> None:
        raw = '{"app_id":"slack"}\n{"app_id":"github"}'
        records = parse_ordered_jsonl(raw, ["slack", "github"])
        self.assertEqual([item["app_id"] for item in records], ["slack", "github"])

    def test_parser_rejects_wrong_order(self) -> None:
        with self.assertRaises(AgentOutputError):
            parse_ordered_jsonl('{"app_id":"github"}\n{"app_id":"slack"}', ["slack", "github"])


if __name__ == "__main__":
    unittest.main()
