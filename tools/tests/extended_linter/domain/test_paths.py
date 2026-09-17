import unittest

import tools.extended_linter.domain.paths as domain_paths


class TestNormalizePath(unittest.TestCase):
    def test_backslashes(self) -> None:
        self.assertEqual(domain_paths.normalize_path("foo\\bar"), "foo/bar")

    def test_leading_dot_slash(self) -> None:
        self.assertEqual(domain_paths.normalize_path("./.cursor/env.sh"), ".cursor/env.sh")
