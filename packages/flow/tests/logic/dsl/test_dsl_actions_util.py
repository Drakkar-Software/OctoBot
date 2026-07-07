import mock
import pytest

import octobot_commons.dsl_interpreter
import octobot_commons.profiles.profile_data as profile_data_import

import octobot_flow.entities
import octobot_flow.logic.dsl.dsl_actions_util


class _RecallableTestOperator(
    octobot_commons.dsl_interpreter.Operator,
    octobot_commons.dsl_interpreter.ReCallableOperatorMixin,
):
    @classmethod
    def get_name(cls) -> str:
        return "test_recallable_operator"


class _NonRecallableTestOperator(octobot_commons.dsl_interpreter.Operator):
    @classmethod
    def get_name(cls) -> str:
        return "test_non_recallable_operator"


class TestIsRecallableDslAction:
    def test_returns_true_for_recallable_top_operator(self):
        dsl_executor = mock.Mock()
        dsl_executor.get_top_operator.return_value = _RecallableTestOperator()
        action = octobot_flow.entities.DSLScriptActionDetails(
            id="action_1",
            dsl_script="test_recallable_operator()",
            resolved_dsl_script="test_recallable_operator()",
        )

        assert octobot_flow.logic.dsl.dsl_actions_util.is_recallable_dsl_action(
            dsl_executor, action
        ) is True
        dsl_executor._interpreter.prepare.assert_called_once_with("test_recallable_operator()")

    def test_returns_false_for_non_recallable_top_operator(self):
        dsl_executor = mock.Mock()
        dsl_executor.get_top_operator.return_value = _NonRecallableTestOperator()
        action = octobot_flow.entities.DSLScriptActionDetails(
            id="action_1",
            dsl_script="test_non_recallable_operator()",
            resolved_dsl_script="test_non_recallable_operator()",
        )

        assert octobot_flow.logic.dsl.dsl_actions_util.is_recallable_dsl_action(
            dsl_executor, action
        ) is False

    def test_returns_false_when_dsl_script_is_empty(self):
        dsl_executor = mock.Mock()
        action = octobot_flow.entities.DSLScriptActionDetails(id="action_1", dsl_script="")

        assert octobot_flow.logic.dsl.dsl_actions_util.is_recallable_dsl_action(
            dsl_executor, action
        ) is False
        dsl_executor._interpreter.prepare.assert_not_called()
