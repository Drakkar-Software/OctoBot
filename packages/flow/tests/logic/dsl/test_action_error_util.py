import pytest

import octobot_commons.errors

import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.logic.dsl.action_error_util


class TestResolveErrorStatement:
    def test_known_status_only(self):
        err = octobot_commons.errors.ErrorStatementEncountered(
            octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value
        )
        error_status, error_message = octobot_flow.logic.dsl.action_error_util.resolve_error_statement(err)
        assert error_status == octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value
        assert error_message == "Not enough funds"

    def test_known_status_with_custom_message(self):
        err = octobot_commons.errors.ErrorStatementEncountered(
            octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value,
            "Balance below threshold",
        )
        error_status, error_message = octobot_flow.logic.dsl.action_error_util.resolve_error_statement(err)
        assert error_status == octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value
        assert error_message == "Balance below threshold"

    def test_unknown_first_argument(self):
        err = octobot_commons.errors.ErrorStatementEncountered("custom failure")
        error_status, error_message = octobot_flow.logic.dsl.action_error_util.resolve_error_statement(err)
        assert error_status == octobot_flow.enums.ActionErrorStatus.DSL_EXECUTION_ERROR.value
        assert error_message == "custom failure"


class TestDefaultMessageForStatus:
    def test_humanizes_snake_case(self):
        assert (
            octobot_flow.logic.dsl.action_error_util.default_message_for_status("not_enough_funds")
            == "Not enough funds"
        )


class TestAbstractActionDetailsComplete:
    def test_sets_error_status_and_error_message(self):
        action = octobot_flow.entities.DSLScriptActionDetails(id="action_1", dsl_script="True")
        action.complete(
            error_status=octobot_flow.enums.ActionErrorStatus.INVALID_ORDER.value,
            error_message="Order volume too small",
        )
        assert action.error_status == octobot_flow.enums.ActionErrorStatus.INVALID_ORDER.value
        assert action.error_message == "Order volume too small"
        assert action.executed_at is not None

    def test_success_leaves_error_message_none(self):
        action = octobot_flow.entities.DSLScriptActionDetails(id="action_1", dsl_script="True")
        action.complete(result={"ok": True})
        assert action.error_message is None
        assert action.error_status is None

    def test_reset_clears_error_message(self):
        action = octobot_flow.entities.DSLScriptActionDetails(id="action_1", dsl_script="True")
        action.complete(
            error_status=octobot_flow.enums.ActionErrorStatus.INTERNAL_ERROR.value,
            error_message="Something failed",
        )
        action.reset()
        assert action.error_message is None
        assert action.error_status is None
