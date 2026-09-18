import unittest

import tools.extended_linter.config.loader as config_loader
import tools.extended_linter.layers.diff_policy as layer_diff
import tools.extended_linter.layers.path_policy as layer_path

CATALOG_AGENT_DOCS_RULES = [
    "agent_docs.no_regression_vs_merge_base",
]

CATALOG_PATH_RULES = [
    "path.deny_repo_tentacles",
    "path.deny_user",
    "path.deny_dotenv",
    "path.deny_cursor_local",
    "path.deny_private_keys",
    "path.deny_known_secret_filenames",
    "path.deny_agent_plans",
    "path.deny_node_web_playwright_e2e",
]

CATALOG_DIFF_RULES = [
    "diff.no_pip_install",
    "diff.no_npm_install",
    "diff.no_git_force_push",
    "diff.no_bare_except",
    "diff.no_subprocess_pip",
    "diff.no_disable_verify",
]


class TestCatalogPathRules(unittest.TestCase):
    def test_each_path_rule_id_present(self) -> None:
        policy = config_loader.load_policy()
        rule_ids = {rule["rule_id"] for rule in policy["path_rules"]}
        self.assertEqual(rule_ids, set(CATALOG_PATH_RULES))

    def test_cursor_local_path(self) -> None:
        policy = config_loader.load_policy()
        violations = layer_path.run([".cursor/env.sh"], policy)
        self.assertEqual(violations[0].rule_id, "path.deny_cursor_local")

    def test_private_key_path(self) -> None:
        policy = config_loader.load_policy()
        violations = layer_path.run(["keys/id_rsa"], policy)
        self.assertEqual(violations[0].rule_id, "path.deny_private_keys")

    def test_secrets_json_path(self) -> None:
        policy = config_loader.load_policy()
        violations = layer_path.run(["config/credentials.json"], policy)
        self.assertEqual(violations[0].rule_id, "path.deny_known_secret_filenames")

    def test_agent_plan_paths(self) -> None:
        policy = config_loader.load_policy()
        plan_scratch = (
            "packages/tentacles/Services/Interfaces/node_web_interface/"
            "PLAN-login-error-display.md"
        )
        violations = layer_path.run([plan_scratch, ".cursor/plans/foo.plan.md"], policy)
        rule_ids = {violation.rule_id for violation in violations}
        self.assertEqual(rule_ids, {"path.deny_agent_plans"})

    def test_node_web_playwright_e2e_path(self) -> None:
        policy = config_loader.load_policy()
        e2e_spec = (
            "packages/tentacles/Services/Interfaces/node_web_interface/"
            "e2e/login-auth-errors.spec.ts"
        )
        violations = layer_path.run([e2e_spec], policy)
        self.assertEqual(violations[0].rule_id, "path.deny_node_web_playwright_e2e")


class TestCatalogAgentDocsRules(unittest.TestCase):
    def test_each_agent_docs_rule_id_present(self) -> None:
        policy = config_loader.load_policy()
        rule_ids = {rule["rule_id"] for rule in policy.get("agent_docs_rules") or []}
        self.assertEqual(rule_ids, set(CATALOG_AGENT_DOCS_RULES))


class TestCatalogDiffRules(unittest.TestCase):
    def test_each_diff_rule_id_present(self) -> None:
        policy = config_loader.load_policy()
        rule_ids = {rule["rule_id"] for rule in policy["diff_rules"]}
        self.assertEqual(rule_ids, set(CATALOG_DIFF_RULES))

    def test_npm_install(self) -> None:
        policy = config_loader.load_policy()
        diff = """diff --git a/x b/x
--- a/x
+++ b/x
@@ -0,0 +1 @@
+npm install left-pad
"""
        violations = layer_diff.run(diff, policy)
        self.assertTrue(any(v.rule_id == "diff.no_npm_install" for v in violations))

    def test_force_push(self) -> None:
        policy = config_loader.load_policy()
        diff = """diff --git a/doc.md b/doc.md
--- a/doc.md
+++ b/doc.md
@@ -1 +1,2 @@
+git push --force origin dev
"""
        violations = layer_diff.run(diff, policy)
        self.assertTrue(any(v.rule_id == "diff.no_git_force_push" for v in violations))

    def test_no_verify(self) -> None:
        policy = config_loader.load_policy()
        diff = """diff --git a/x b/x
--- a/x
+++ b/x
@@ -0,0 +1 @@
+git commit --no-verify -m "x"
"""
        violations = layer_diff.run(diff, policy)
        self.assertTrue(any(v.rule_id == "diff.no_disable_verify" for v in violations))
