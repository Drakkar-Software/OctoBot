import unittest

import tools.extended_linter.cli as linter_cli


class TestCliHelp(unittest.TestCase):
    def test_help_exits_zero(self) -> None:
        with self.assertRaises(SystemExit) as exit_info:
            linter_cli.main(["--help"])
        self.assertEqual(exit_info.exception.code, 0)
