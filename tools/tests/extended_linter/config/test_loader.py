import unittest

import tools.extended_linter.config.loader as config_loader


class TestLoadPolicy(unittest.TestCase):
    def test_load_default_policy(self) -> None:
        policy = config_loader.load_policy()
        self.assertEqual(policy["policy_version"], 1)
        self.assertTrue(policy.get("path_rules"))
        self.assertTrue(policy.get("diff_rules"))
