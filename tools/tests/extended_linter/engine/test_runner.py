import pathlib
import unittest

import mock

import tools.extended_linter.engine.runner as engine_runner


class TestRunnerStopsOnMissingBase(unittest.TestCase):
    def test_returns_git_violation_without_path_checks(self) -> None:
        with mock.patch(
            "tools.extended_linter.layers.git_scope.verify_merge_base",
            return_value=[
                mock.Mock(rule_id="git.merge_base_missing"),
            ],
        ) as verify_mock:
            with mock.patch(
                "tools.extended_linter.layers.git_scope.list_changed_paths",
            ) as list_mock:
                config = engine_runner.RunnerConfig(
                    repo_root=pathlib.Path("."),
                    base_ref="origin/dev",
                    policy_path=None,
                    skip_tentacles_reinstall=True,
                )
                violations = engine_runner.run(config)
        verify_mock.assert_called_once()
        list_mock.assert_not_called()
        self.assertEqual(len(violations), 1)
