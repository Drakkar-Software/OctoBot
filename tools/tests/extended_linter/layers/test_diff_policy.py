import unittest

import tools.extended_linter.layers.diff_policy as layer_diff


SAMPLE_DIFF = """diff --git a/foo.py b/foo.py
index 111..222 100644
--- a/foo.py
+++ b/foo.py
@@ -1,2 +1,3 @@
 line
+pip install requests
 more
"""


class TestDiffNoPipInstall(unittest.TestCase):
    def test_pip_install_on_added_line(self) -> None:
        policy = {
            "diff_rules": [
                {
                    "rule_id": "diff.no_pip_install",
                    "patterns": [r"\bpip3?\s+install\b"],
                    "hint": "no pip",
                }
            ]
        }
        violations = layer_diff.run(SAMPLE_DIFF, policy)
        self.assertTrue(any(v.rule_id == "diff.no_pip_install" for v in violations))


class TestDiffSubprocessPip(unittest.TestCase):
    def test_subprocess_pip_line(self) -> None:
        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1 +1,2 @@
+    subprocess.run(["pip", "install", "x"])
"""
        policy = {
            "diff_rules": [
                {
                    "rule_id": "diff.no_subprocess_pip",
                    "kind": "subprocess_package_manager",
                    "hint": "no",
                }
            ]
        }
        violations = layer_diff.run(diff, policy)
        self.assertEqual(violations[0].rule_id, "diff.no_subprocess_pip")
