import json
import unittest

import tools.extended_linter.domain.models as domain_models
import tools.extended_linter.reporting.format as reporting_format


class TestFormatText(unittest.TestCase):
    def test_ok_message(self) -> None:
        self.assertIn("OK", reporting_format.format_text([]))

    def test_violation_block(self) -> None:
        violation = domain_models.Violation(
            rule_id="diff.no_pip_install",
            file="a.py",
            line=3,
            hint="no pip",
        )
        text = reporting_format.format_text([violation])
        self.assertIn("diff.no_pip_install", text)
        self.assertIn("a.py:3", text)


class TestFormatJson(unittest.TestCase):
    def test_json_payload(self) -> None:
        payload = json.loads(reporting_format.format_json([]))
        self.assertTrue(payload["ok"])
