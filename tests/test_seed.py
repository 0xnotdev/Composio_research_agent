from pathlib import Path
import unittest

from agent.seed import load_seeds


class SeedRosterTests(unittest.TestCase):
    def test_assignment_roster_is_complete_and_balanced(self) -> None:
        seeds = load_seeds(Path("data/apps_100.json"))
        self.assertEqual(len(seeds), 100)
        self.assertEqual(len({seed.app_id for seed in seeds}), 100)
        self.assertEqual(len({seed.category for seed in seeds}), 10)

    def test_known_special_cases_are_retained(self) -> None:
        seeds = {seed.app_id: seed for seed in load_seeds(Path("data/apps_100.json"))}
        self.assertEqual(seeds["sherlock"].hint, "github.com/sherlock-project/sherlock")
        self.assertEqual(seeds["mermaid_cli"].hint, "github.com/mermaid-js/mermaid-cli")
        self.assertEqual(seeds["sentry"].hint, "docs.sentry.io/api")


if __name__ == "__main__":
    unittest.main()
