import octobot_commons.dsl_interpreter

import octobot_flow.entities.automations.post_iteration_actions_details as post_iteration_actions_details_module


class TestPostIterationClear:
    def test_removes_only_updated_exchange_account_elements(self):
        post_iteration_payload = {
            "updated_exchange_account_elements": {"trades": []},
            "stop_automation": False,
            "configuration_update": "run_octobot_process('folder')",
        }
        post_iteration_actions_details_module.PostIterationActionsDetails.post_iteration_clear(
            post_iteration_payload
        )
        assert "updated_exchange_account_elements" not in post_iteration_payload
        assert post_iteration_payload["stop_automation"] is False
        assert post_iteration_payload["configuration_update"] == "run_octobot_process('folder')"


class TestPostIterationClearFromActionResult:
    def test_clears_nested_recall_post_iteration(self):
        post_iteration_name = post_iteration_actions_details_module.PostIterationActionsDetails.__name__
        action_result = {
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__: {
                "last_execution_result": {
                    post_iteration_name: {
                        "updated_exchange_account_elements": {"trades": []},
                        "stop_automation": False,
                    },
                    "pid": 42,
                },
            }
        }
        post_iteration_actions_details_module.PostIterationActionsDetails.post_iteration_clear_from_action_result(
            action_result
        )
        inner_post_iteration = action_result[
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__
        ]["last_execution_result"][post_iteration_name]
        assert "updated_exchange_account_elements" not in inner_post_iteration
        assert inner_post_iteration["stop_automation"] is False
        assert action_result[
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__
        ]["last_execution_result"]["pid"] == 42

    def test_top_level_stop_automation_unchanged(self):
        post_iteration_name = post_iteration_actions_details_module.PostIterationActionsDetails.__name__
        action_result = {
            post_iteration_name: {
                "stop_automation": True,
            }
        }
        post_iteration_actions_details_module.PostIterationActionsDetails.post_iteration_clear_from_action_result(
            action_result
        )
        assert action_result[post_iteration_name] == {"stop_automation": True}

    def test_top_level_configuration_update_unchanged(self):
        post_iteration_name = post_iteration_actions_details_module.PostIterationActionsDetails.__name__
        configuration_update = "run_octobot_process('folder')"
        action_result = {
            post_iteration_name: {
                "configuration_update": configuration_update,
            }
        }
        post_iteration_actions_details_module.PostIterationActionsDetails.post_iteration_clear_from_action_result(
            action_result
        )
        assert action_result[post_iteration_name]["configuration_update"] == configuration_update

    def test_clears_top_level_and_nested_when_both_present(self):
        post_iteration_name = post_iteration_actions_details_module.PostIterationActionsDetails.__name__
        action_result = {
            post_iteration_name: {
                "updated_exchange_account_elements": {"trades": [{"id": "top"}]},
            },
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__: {
                "last_execution_result": {
                    post_iteration_name: {
                        "updated_exchange_account_elements": {"trades": [{"id": "nested"}]},
                    },
                },
            },
        }
        post_iteration_actions_details_module.PostIterationActionsDetails.post_iteration_clear_from_action_result(
            action_result
        )
        assert "updated_exchange_account_elements" not in action_result[post_iteration_name]
        nested_post_iteration = action_result[
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__
        ]["last_execution_result"][post_iteration_name]
        assert "updated_exchange_account_elements" not in nested_post_iteration

    def test_recall_without_post_iteration_preserves_inner_fields(self):
        action_result = {
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__: {
                "last_execution_result": {
                    "pid": 42,
                    "init_state_ok": True,
                },
            }
        }
        post_iteration_actions_details_module.PostIterationActionsDetails.post_iteration_clear_from_action_result(
            action_result
        )
        inner_last_result = action_result[
            octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__
        ]["last_execution_result"]
        assert inner_last_result["pid"] == 42
        assert inner_last_result["init_state_ok"] is True

    def test_non_recall_result_without_post_iteration_is_no_op(self):
        action_result = {"pid": 42}
        post_iteration_actions_details_module.PostIterationActionsDetails.post_iteration_clear_from_action_result(
            action_result
        )
        assert action_result == {"pid": 42}
