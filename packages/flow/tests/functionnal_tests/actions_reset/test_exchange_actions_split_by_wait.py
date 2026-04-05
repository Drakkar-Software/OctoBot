import pytest
import time
import asyncio
import mock

import octobot_commons.constants as common_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import tentacles.Meta.DSL_operators.python_std_operators.base_resetting_operators as resetting_operators
import tentacles.Meta.DSL_operators.python_std_operators.base_time_operators as base_time_operators

import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    global_state,
    btc_usdc_global_state,
    auth_details,
    actions_with_market_orders,
    resolved_actions,
    actions_with_create_limit_orders,
    actions_with_cancel_limit_orders,
    create_wait_action,
)


ADDED_COIN_SYMBOL = "BTC"

@pytest.mark.asyncio
async def test_exchange_actions_creating_and_waiting_and_cancelling_limit(
    btc_usdc_global_state: dict, auth_details: octobot_flow.entities.UserAuthentication,
    actions_with_create_limit_orders: list[dict], actions_with_cancel_limit_orders: list[dict]
):
    wait_action = create_wait_action(50, 100, dependencies=[{"action_id": actions_with_create_limit_orders[0]["id"]}])
    actions_with_cancel_limit_orders[0]["id"] = "action_cancel"
    actions_with_cancel_limit_orders[0]["dependencies"] = [{"action_id": wait_action["id"]}]
    actions_to_execute = actions_with_create_limit_orders + [wait_action] + actions_with_cancel_limit_orders

    assert len(actions_to_execute) == 3
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
    ):
        t0 = time.time()
        # 1. execute create limit order action
        automation_state = octobot_flow.entities.AutomationState.from_dict(btc_usdc_global_state)
        automation_state.update_automation_actions(
resolved_actions(actions_to_execute),
        )
        async with octobot_flow.AutomationJob(automation_state, [], auth_details) as automations_job:
            await automations_job.run()

        # check bot actions execution
        actions = automations_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_to_execute)
        create_limit_action = actions[0]
        wait_action = actions[1]
        cancel_action = actions[2]
        assert create_limit_action.executed_at is not None and create_limit_action.executed_at > 0 # create order action has been executed
        assert isinstance(create_limit_action, octobot_flow.entities.AbstractActionDetails)
        assert create_limit_action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        assert isinstance(create_limit_action.result, dict)
        assert "created_orders" in create_limit_action.result
        order = create_limit_action.result["created_orders"][0]
        assert order[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value] == "BTC/USDC"
        assert 0 < order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] < 0.001
        assert order[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] == "limit"
        assert order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == "buy"
        assert 5_000 < order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] < 10_000_000

        for action in [wait_action, cancel_action]:
            assert action.executed_at is None
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
        
        # immediately execute wait action
        assert automations_job.automation_state.automation.execution.current_execution.scheduled_to == 0

        # 2.A execute wait action 1/3
        automation_state_2 = automations_job.automation_state
        with mock.patch.object(asyncio, "sleep", mock.AsyncMock(return_value=None)) as sleep_mock:
            async with octobot_flow.AutomationJob(automation_state_2, [], auth_details) as automations_job_2:
                await automations_job_2.run()
                for call in sleep_mock.mock_calls:
                    # there was no call for the wait action
                    assert call.args[0] < 1
        
        # check bot actions execution
        actions = automations_job_2.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_to_execute)
        create_limit_action = actions[0]
        assert create_limit_action.executed_at is not None and create_limit_action.executed_at > 0
        # special case: wait action is executed and automatically reset since less than 50 seconds have passed
        wait_action = actions[1]
        assert wait_action.executed_at is None
        assert wait_action.result is None
        assert wait_action.error_status is None
        assert isinstance(wait_action.previous_execution_result, dict)
        rescheduled_parameters = wait_action.get_rescheduled_parameters()
        assert dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY in rescheduled_parameters
        last_execution_result = dsl_interpreter.ReCallingOperatorResult.from_dict(
            rescheduled_parameters[dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY][
                dsl_interpreter.ReCallingOperatorResult.__name__
            ]
        )
        assert isinstance(last_execution_result.last_execution_result, dict)
        waiting_time_1 = last_execution_result.last_execution_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value]
        assert 0 < waiting_time_1 <= 100
        cancel_action = actions[2]
        assert cancel_action.executed_at is None


        # 2.B execute wait action 2/3
        automation_state_3 = automations_job.automation_state
        with mock.patch.object(asyncio, "sleep", mock.AsyncMock(return_value=None)) as sleep_mock:
            async with octobot_flow.AutomationJob(automation_state_3, [], auth_details) as automations_job_3:
                await automations_job_3.run()
                for call in sleep_mock.mock_calls:
                    # there was no call for the wait action
                    assert call.args[0] < 1
        
        # check bot actions execution
        actions = automations_job_3.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_to_execute)
        create_limit_action = actions[0]
        assert create_limit_action.executed_at is not None and create_limit_action.executed_at > 0
        # special case: wait action is executed and automatically reset since less than 50 seconds have passed
        wait_action = actions[1]
        assert wait_action.executed_at is None
        assert wait_action.result is None
        assert wait_action.error_status is None
        assert isinstance(wait_action.previous_execution_result, dict)
        rescheduled_parameters = wait_action.get_rescheduled_parameters()
        assert dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY in rescheduled_parameters
        last_execution_result = dsl_interpreter.ReCallingOperatorResult.from_dict(
            rescheduled_parameters[dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY][
                dsl_interpreter.ReCallingOperatorResult.__name__
            ]
        )
        assert isinstance(last_execution_result.last_execution_result, dict)
        waiting_time_2 = last_execution_result.last_execution_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value]
        assert waiting_time_2 < waiting_time_1 # there is now less time to wait than during the first time
        assert 0 < waiting_time_2 <= 100
        cancel_action = actions[2]
        assert cancel_action.executed_at is None

        # 2.C execute wait action 3/3
        automation_state_4 = automations_job.automation_state
        with (
            mock.patch.object(asyncio, "sleep", mock.AsyncMock(return_value=None)) as sleep_mock,
            mock.patch.object(time, "time", mock.Mock(return_value=t0 + waiting_time_1 + 50)),
        ):
            async with octobot_flow.AutomationJob(automation_state_4, [], auth_details) as automations_job_4:
                await automations_job_4.run()
                for call in sleep_mock.mock_calls:
                    # there was no call for the wait action
                    assert call.args[0] < 1
        
        # wait bot actions has now been executed
        actions = automations_job_4.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_to_execute)
        create_limit_action = actions[0]
        assert create_limit_action.executed_at is not None and create_limit_action.executed_at > 0
        # special case: wait action is executed and automatically reset since less than 50 seconds have passed
        wait_action = actions[1]
        assert wait_action.executed_at is not None and wait_action.executed_at > 0
        assert wait_action.result is None
        assert wait_action.error_status is None
        assert isinstance(wait_action.previous_execution_result, dict)
        cancel_action = actions[2]
        assert cancel_action.executed_at is None

        # 3. execute cancel limit order action
        automation_state_4 = automations_job_4.automation_state
        async with octobot_flow.AutomationJob(automation_state_4, [], auth_details) as automations_job_4:
            await automations_job_4.run()

        # check bot actions execution
        actions = automations_job_4.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_to_execute)
        create_limit_action = actions[0]
        assert create_limit_action.executed_at is not None and create_limit_action.executed_at > 0
        wait_action = actions[1]
        assert wait_action.executed_at is not None and wait_action.executed_at > 0
        cancel_action = actions[2]
        assert cancel_action.executed_at is not None and cancel_action.executed_at > 0
        assert cancel_action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        assert isinstance(cancel_action.result, dict)
        assert "cancelled_orders" in cancel_action.result
        cancelled = cancel_action.result["cancelled_orders"]
        assert len(cancelled) == 1
        assert len(cancelled[0]) > 2  # id of the cancelled order

        after_execution_dump = automations_job_4.dump()
        after_execution_portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert "USDC" in after_execution_portfolio_content
        for asset_type in [common_constants.PORTFOLIO_AVAILABLE, common_constants.PORTFOLIO_TOTAL]:
            assert 5 <= after_execution_portfolio_content["USDC"][asset_type] < 10_000_000
    

@pytest.mark.asyncio
async def test_exchange_actions_creating_and_waiting_with_condition_that_is_not_reevaluated(
    btc_usdc_global_state: dict, auth_details: octobot_flow.entities.UserAuthentication,
    actions_with_create_limit_orders: list[dict], actions_with_cancel_limit_orders: list[dict]
):
    """
    DSL like ``wait(..., return_remaining_time=True) if now_ms() < N else None`` must resume as a plain
    ``wait(...)`` with ``last_execution_result`` so the ``if`` is not re-evaluated. Otherwise a second run
    could see ``now_ms() >= N`` and take the else branch instead of continuing the wait.
    """
    wait_threshold_ms = 2_000_000
    wait_action = {
        "id": "action_wait",
        "dsl_script": (
            f"wait(50, 100, return_remaining_time=True) if now_ms() < {wait_threshold_ms} else None"
        ),
        "dependencies": [{"action_id": actions_with_create_limit_orders[0]["id"]}],
    }
    actions_with_cancel_limit_orders[0]["id"] = "action_cancel"
    actions_with_cancel_limit_orders[0]["dependencies"] = [{"action_id": wait_action["id"]}]
    actions_to_execute = actions_with_create_limit_orders + [wait_action] + actions_with_cancel_limit_orders

    now_ms_call_counter = {"count": 0}

    def tracked_now_ms_compute(operator_self):
        now_ms_call_counter["count"] += 1
        if now_ms_call_counter["count"] == 1:
            return wait_threshold_ms - 1
        return wait_threshold_ms + 1

    assert len(actions_to_execute) == 3
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(base_time_operators.NowMsOperator, "compute", tracked_now_ms_compute),
    ):
        t0 = time.time()
        automation_state = octobot_flow.entities.AutomationState.from_dict(btc_usdc_global_state)
        automation_state.update_automation_actions(
            resolved_actions(actions_to_execute),
        )
        async with octobot_flow.AutomationJob(automation_state, [], auth_details) as automations_job:
            await automations_job.run()

        actions = automations_job.automation_state.automation.actions_dag.actions
        create_limit_action = actions[0]
        wait_action_state = actions[1]
        cancel_action = actions[2]
        assert create_limit_action.executed_at is not None and create_limit_action.executed_at > 0
        assert create_limit_action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        assert wait_action_state.executed_at is None
        assert cancel_action.executed_at is None
        assert now_ms_call_counter["count"] == 0

        automation_state_2 = automations_job.automation_state
        with mock.patch.object(asyncio, "sleep", mock.AsyncMock(return_value=None)) as sleep_mock:
            async with octobot_flow.AutomationJob(automation_state_2, [], auth_details) as automations_job_2:
                await automations_job_2.run()
                for call in sleep_mock.mock_calls:
                    assert call.args[0] < 1

        assert now_ms_call_counter["count"] == 1

        actions = automations_job_2.automation_state.automation.actions_dag.actions
        wait_action_state = actions[1]
        assert wait_action_state.executed_at is None
        script_override = dsl_interpreter.ReCallingOperatorResult.get_script_override(
            wait_action_state.previous_execution_result
        )
        assert script_override is not None
        assert script_override.startswith("wait(")
        assert " if " not in script_override
        rescheduled_parameters = wait_action_state.get_rescheduled_parameters()
        last_execution_result = dsl_interpreter.ReCallingOperatorResult.from_dict(
            rescheduled_parameters[dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY][
                dsl_interpreter.ReCallingOperatorResult.__name__
            ]
        )
        assert last_execution_result.last_execution_result is not None
        waiting_time_1 = last_execution_result.last_execution_result[
            dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value
        ]
        assert 0 < waiting_time_1 <= 100

        automation_state_3 = automations_job_2.automation_state
        with mock.patch.object(asyncio, "sleep", mock.AsyncMock(return_value=None)) as sleep_mock:
            async with octobot_flow.AutomationJob(automation_state_3, [], auth_details) as automations_job_3:
                await automations_job_3.run()
                for call in sleep_mock.mock_calls:
                    assert call.args[0] < 1

        assert now_ms_call_counter["count"] == 1

        actions = automations_job_3.automation_state.automation.actions_dag.actions
        wait_action_state = actions[1]
        assert wait_action_state.executed_at is None
        rescheduled_parameters = wait_action_state.get_rescheduled_parameters()
        last_execution_result = dsl_interpreter.ReCallingOperatorResult.from_dict(
            rescheduled_parameters[dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY][
                dsl_interpreter.ReCallingOperatorResult.__name__
            ]
        )
        assert last_execution_result.last_execution_result is not None
        waiting_time_2 = last_execution_result.last_execution_result[
            dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value
        ]
        assert waiting_time_2 < waiting_time_1
        assert 0 < waiting_time_2 <= 100

        automation_state_4 = automations_job_3.automation_state
        with (
            mock.patch.object(asyncio, "sleep", mock.AsyncMock(return_value=None)) as sleep_mock,
            mock.patch.object(time, "time", mock.Mock(return_value=t0 + waiting_time_1 + 50)),
        ):
            async with octobot_flow.AutomationJob(automation_state_4, [], auth_details) as automations_job_4:
                await automations_job_4.run()
                for call in sleep_mock.mock_calls:
                    assert call.args[0] < 1

        actions = automations_job_4.automation_state.automation.actions_dag.actions
        wait_action_state = actions[1]
        assert wait_action_state.executed_at is not None and wait_action_state.executed_at > 0
        cancel_action = actions[2]
        assert cancel_action.executed_at is None

        automation_state_5 = automations_job_4.automation_state
        async with octobot_flow.AutomationJob(automation_state_5, [], auth_details) as automations_job_5:
            await automations_job_5.run()

        actions = automations_job_5.automation_state.automation.actions_dag.actions
        cancel_action = actions[2]
        assert cancel_action.executed_at is not None and cancel_action.executed_at > 0
        assert cancel_action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value