import pathlib
import unittest

import mock

import tools.extended_linter.layers.git_scope as layer_git


class TestVerifyMergeBase(unittest.TestCase):
    def test_missing_ref_violation(self) -> None:
        with mock.patch("subprocess.run") as run_mock:
            run_mock.return_value = mock.Mock(returncode=1, stderr="bad ref")
            violations = layer_git.verify_merge_base(
                pathlib.Path("."),
                "origin/dev",
                {"git_rules": [{"rule_id": "git.merge_base_missing", "hint": "fetch"}]},
            )
        self.assertEqual(violations[0].rule_id, "git.merge_base_missing")
