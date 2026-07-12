import unittest

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_flow.entities.actions.action_details as action_details
import octobot_flow.entities.automations.octobot_process_state as octobot_process_state_module


class TestParseOctobotProcessState(unittest.TestCase):
    def test_parse_octobot_process_state_returns_none_for_empty_dict(self):
        self.assertIsNone(octobot_process_state_module.parse_octobot_process_state({}))

    def test_parse_octobot_process_state_returns_state_for_valid_recall_dict(self):
        recall_dict = {
            "http_base_url": "http://127.0.0.1:5002",
            "web_port": 5002,
            "node_port": 6002,
            "user_root": "/tmp/user",
            "user_folder": "automation-a",
            "log_folder": "/tmp/log",
            "profile_id": None,
            "pid": 12345,
            "init_state_ok": True,
            "executor_id": "exec-1",
        }
        parsed_state = octobot_process_state_module.parse_octobot_process_state(recall_dict)
        self.assertIsInstance(parsed_state, octobot_process_state_module.OctobotProcessState)
        self.assertEqual(parsed_state.http_base_url, "http://127.0.0.1:5002")
        self.assertEqual(parsed_state.web_port, 5002)
        self.assertTrue(parsed_state.init_state_ok)


class TestIsRunOctobotProcessDslAction(unittest.TestCase):
    def test_is_run_octobot_process_dsl_action_returns_true_for_run_octobot_process_script(self):
        dsl_action = action_details.DSLScriptActionDetails(
            id="action-1",
            dsl_script='run_octobot_process("folder", {}, [])',
        )
        self.assertTrue(
            octobot_process_state_module.is_run_octobot_process_dsl_action(dsl_action)
        )

    def test_is_run_octobot_process_dsl_action_returns_false_for_other_dsl_script(self):
        dsl_action = action_details.DSLScriptActionDetails(
            id="action-1",
            dsl_script='other_operator("folder")',
        )
        self.assertFalse(
            octobot_process_state_module.is_run_octobot_process_dsl_action(dsl_action)
        )

    def test_is_run_octobot_process_dsl_action_uses_resolved_dsl_script_when_set(self):
        dsl_action = action_details.DSLScriptActionDetails(
            id="action-1",
            dsl_script='placeholder',
            resolved_dsl_script='run_octobot_process("folder", {}, [])',
        )
        self.assertTrue(
            octobot_process_state_module.is_run_octobot_process_dsl_action(dsl_action)
        )


class TestRecallInnerFromActionResult(unittest.TestCase):
    def test_recall_inner_from_action_result_unwraps_recalling_operator_result(self):
        inner_recall = {
            "http_base_url": "http://127.0.0.1:5002",
            "web_port": 5002,
            "pid": 12345,
        }
        recall_wrapper = dsl_interpreter.ReCallingOperatorResult(
            keyword="run_octobot_process",
            reset_to_id="action-1",
            last_execution_result=inner_recall,
        )
        action_result = {
            dsl_interpreter.ReCallingOperatorResult.__name__: recall_wrapper.to_dict(),
        }
        inner = octobot_process_state_module.recall_inner_from_action_result(action_result)
        self.assertEqual(inner, inner_recall)
