import pathlib
import subprocess
import tempfile
import unittest

import mock

import tools.extended_linter.layers.git_scope as layer_git

POLICY = {"git_rules": [{"rule_id": "git.merge_base_missing", "hint": "fetch"}]}


class TestVerifyMergeBase(unittest.TestCase):
    def test_missing_ref_violation(self) -> None:
        with mock.patch("subprocess.run") as run_mock:
            run_mock.return_value = mock.Mock(returncode=1, stderr="bad ref")
            violations = layer_git.verify_merge_base(
                pathlib.Path("."),
                "origin/dev",
                POLICY,
            )
        self.assertEqual(violations[0].rule_id, "git.merge_base_missing")

    def test_unrelated_histories_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            self._git(repo, "init", "-q", "-b", "dev")
            self._git(repo, "commit", "-q", "--allow-empty", "-m", "base")
            self._git(repo, "update-ref", "refs/remotes/origin/dev", "dev")
            self._git(repo, "checkout", "-q", "--orphan", "feat")
            self._git(repo, "commit", "-q", "--allow-empty", "-m", "orphan")
            violations = layer_git.verify_merge_base(repo, "refs/remotes/origin/dev", POLICY)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, "git.merge_base_missing")

    def test_related_history_no_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            self._git(repo, "init", "-q", "-b", "dev")
            self._git(repo, "commit", "-q", "--allow-empty", "-m", "base")
            self._git(repo, "update-ref", "refs/remotes/origin/dev", "dev")
            self._git(repo, "checkout", "-q", "-b", "feat")
            self._git(repo, "commit", "-q", "--allow-empty", "-m", "feat")
            violations = layer_git.verify_merge_base(repo, "refs/remotes/origin/dev", POLICY)
        self.assertEqual(violations, [])

    @staticmethod
    def _git(repo: pathlib.Path, *args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=repo,
            check=True,
            capture_output=True,
        )
