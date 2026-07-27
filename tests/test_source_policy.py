from pathlib import Path
import unittest

from agent.models import AppSeed
from agent.source_policy import SourcePolicy


class SourcePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = SourcePolicy.load(Path("data/app_source_policy.json"))

    def test_accepts_vendor_subdomain_and_rejects_lookalike(self) -> None:
        slack = AppSeed("slack", "Slack", "Communications", "slack.com")
        self.assertTrue(self.policy.is_accepted(slack, "https://api.slack.com/authentication"))
        self.assertFalse(self.policy.is_accepted(slack, "https://slack.example.com/oauth"))
        self.assertFalse(self.policy.is_accepted(slack, "http://api.slack.com/authentication"))

    def test_official_github_repositories_are_path_scoped(self) -> None:
        sherlock = AppSeed("sherlock", "Sherlock", "Data", "github.com/sherlock-project/sherlock")
        self.assertTrue(self.policy.is_accepted(sherlock, "https://github.com/sherlock-project/sherlock/blob/master/README.md"))
        self.assertFalse(self.policy.is_accepted(sherlock, "https://github.com/other/project"))

    def test_ambiguous_hint_requires_manual_policy_approval(self) -> None:
        paygent = AppSeed("paygent_connect", "Paygent Connect", "Finance", "paygent (NMI-powered)")
        self.assertFalse(self.policy.is_accepted(paygent, "https://example.com/docs"))
