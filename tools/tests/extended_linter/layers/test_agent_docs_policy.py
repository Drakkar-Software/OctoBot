import datetime
import unittest

import tools.extended_linter.config.loader as config_loader
import tools.extended_linter.layers.agent_docs_policy as layer_agent_docs

_BASE_AGENTS = """# Agents: example

## Last reviewed

- 2026-09-18
"""

_POLICY_GLOBS = [
    "**/AGENTS.md",
    ".cursor/skills/**/SKILL.md",
    ".cursor/README.md",
    ".cursor/rules/**",
    "CONTRIBUTING-agent.md",
    "tools/**/README.md",
    "tools/**/ARCHITECTURE.md",
]


class TestParseLastReviewedDate(unittest.TestCase):
    def test_parses_date_under_section(self) -> None:
        self.assertEqual(
            layer_agent_docs.parse_last_reviewed_date(_BASE_AGENTS),
            datetime.date(2026, 9, 18),
        )

    def test_missing_section_returns_none(self) -> None:
        self.assertIsNone(layer_agent_docs.parse_last_reviewed_date("# Agents\n"))


class TestShouldFlagShrink(unittest.TestCase):
    def test_large_shrink_flags(self) -> None:
        self.assertTrue(layer_agent_docs.should_flag_shrink(30, 15, 5))

    def test_small_shrink_passes(self) -> None:
        self.assertFalse(layer_agent_docs.should_flag_shrink(30, 28, 5))


class TestMatchesAgentDocPath(unittest.TestCase):
    def test_skill_path_matches(self) -> None:
        self.assertTrue(
            layer_agent_docs.matches_agent_doc_path(
                ".cursor/skills/octobot-cloud/SKILL.md",
                _POLICY_GLOBS,
            )
        )

    def test_package_readme_does_not_match(self) -> None:
        self.assertFalse(
            layer_agent_docs.matches_agent_doc_path(
                "packages/foo/README.md",
                _POLICY_GLOBS,
            )
        )

    def test_mdc_rule_matches(self) -> None:
        self.assertTrue(
            layer_agent_docs.matches_agent_doc_path(
                ".cursor/rules/octobot-cloud.mdc",
                _POLICY_GLOBS,
            )
        )


class TestRegressionReasons(unittest.TestCase):
    def test_backdated_last_reviewed(self) -> None:
        head = _BASE_AGENTS.replace("2026-09-18", "2026-09-16")
        reasons = layer_agent_docs.regression_reasons(
            _BASE_AGENTS,
            head,
            5,
            doc_path="packages/protocol/AGENTS.md",
        )
        self.assertTrue(any("Last reviewed regressed" in reason for reason in reasons))

    def test_forward_last_reviewed_with_growth_passes(self) -> None:
        head = _BASE_AGENTS + "\n## Extra\n\nMore boundary docs.\n"
        reasons = layer_agent_docs.regression_reasons(_BASE_AGENTS, head, 5)
        self.assertEqual(reasons, [])

    def test_shrink_message_includes_path(self) -> None:
        head = "line\n" * 5
        base = "line\n" * 20
        reasons = layer_agent_docs.regression_reasons(
            base,
            head,
            5,
            doc_path=".cursor/skills/foo/SKILL.md",
        )
        self.assertTrue(
            any("Agent doc `.cursor/skills/foo/SKILL.md` shrank" in r for r in reasons)
        )


class TestCatalogAgentDocsRule(unittest.TestCase):
    def test_agent_docs_rule_in_policy(self) -> None:
        policy = config_loader.load_policy()
        rule_ids = {rule["rule_id"] for rule in policy.get("agent_docs_rules") or []}
        self.assertIn("agent_docs.no_regression_vs_merge_base", rule_ids)
