import unittest

import tools.extended_linter.layers.path_policy as layer_path


class TestIsRepoRootTentacles(unittest.TestCase):
    def test_packages_tentacles_allowed(self) -> None:
        policy = {
            "path_rules": [
                {
                    "rule_id": "path.deny_repo_tentacles",
                    "kind": "repo_root_tentacles",
                    "hint": "no",
                }
            ]
        }
        violations = layer_path.run(
            ["packages/tentacles/Trading/foo.py"],
            policy,
        )
        self.assertEqual(violations, [])

    def test_repo_root_tentacles_denied(self) -> None:
        policy = {
            "path_rules": [
                {
                    "rule_id": "path.deny_repo_tentacles",
                    "kind": "repo_root_tentacles",
                    "hint": "no",
                }
            ]
        }
        violations = layer_path.run(["tentacles/Trading/x.py"], policy)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, "path.deny_repo_tentacles")


class TestPathDenyUser(unittest.TestCase):
    def test_user_path_denied(self) -> None:
        policy = {
            "path_rules": [
                {
                    "rule_id": "path.deny_user",
                    "globs": ["user/**", "**/user/**"],
                    "hint": "local",
                }
            ]
        }
        violations = layer_path.run(["user/config.json"], policy)
        self.assertEqual(violations[0].rule_id, "path.deny_user")
