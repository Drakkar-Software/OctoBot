import unittest

import tools.extended_linter.hooks.tentacles as hooks_tentacles


class TestDiffTouchesTentaclesSources(unittest.TestCase):
    def test_packages_tentacles_true(self) -> None:
        self.assertTrue(
            hooks_tentacles.diff_touches_tentacles_sources(
                ["packages/tentacles/Trading/x.py"]
            )
        )

    def test_other_paths_false(self) -> None:
        self.assertFalse(
            hooks_tentacles.diff_touches_tentacles_sources(["packages/trading/x.py"])
        )
