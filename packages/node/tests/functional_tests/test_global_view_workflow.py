#  Drakkar-Software OctoBot-Node

import asyncio
import pathlib

import mock
import pytest

import octobot_node.scheduler.api as scheduler_api_module
import octobot_node.scheduler.tasks as scheduler_tasks_module

from tests.functional_tests.util import global_view_workflow as global_view_workflow_util
from tests.scheduler import temp_dbos_scheduler


@pytest.fixture
def global_view_temp_dbos_scheduler(temp_dbos_scheduler):
    return temp_dbos_scheduler


@pytest.mark.asyncio
class TestGlobalViewWorkflowFunctional:
    async def test_global_view_workflow_updates_all_accounts(
        self,
        tmp_path: pathlib.Path,
        global_view_temp_dbos_scheduler,
    ):
        async with global_view_workflow_util.global_view_functional_environment(tmp_path) as environment:
            workflow_result = await asyncio.wait_for(
                global_view_workflow_util.enqueue_and_await_global_view_refresh(),
                timeout=global_view_workflow_util.WORKFLOW_RESULT_TIMEOUT_SECONDS,
            )
            assert workflow_result["refreshed_accounts"] == 3

            user_id = environment["user_id"]
            account_provider = environment["account_provider"]
            real_account = account_provider.get_item(user_id, global_view_workflow_util.ACCOUNT_REAL_ID)
            sim_account_1 = account_provider.get_item(user_id, global_view_workflow_util.ACCOUNT_SIM_1_ID)
            sim_account_2 = account_provider.get_item(user_id, global_view_workflow_util.ACCOUNT_SIM_2_ID)

            global_view_workflow_util.assert_real_account_assets(real_account)
            global_view_workflow_util.assert_simulated_account_assets(sim_account_1, expected_total=1000.0)
            global_view_workflow_util.assert_simulated_account_assets(sim_account_2, expected_total=1000.0)
            assert real_account.updated_at is not None
            assert sim_account_1.updated_at is not None
            assert sim_account_2.updated_at is not None

    async def test_global_view_workflow_triggers_automation_on_filled_order(
        self,
        tmp_path: pathlib.Path,
        global_view_temp_dbos_scheduler,
    ):
        matching_automation = global_view_workflow_util.build_running_automation_state(
            global_view_workflow_util.AUTOMATION_FILL_ID,
            account_id=global_view_workflow_util.ACCOUNT_SIM_1_ID,
            order_ids=[global_view_workflow_util.ORDER_FILL_ID],
        )
        non_matching_automation = global_view_workflow_util.build_running_automation_state(
            global_view_workflow_util.AUTOMATION_NO_TRIGGER_ID,
            account_id=global_view_workflow_util.ACCOUNT_SIM_1_ID,
            order_ids=[global_view_workflow_util.ORDER_STAYS_OPEN_ID],
        )
        trigger_calls: list[str] = []

        async def record_forced_trigger(automation_id: str, user_id: str) -> None:
            trigger_calls.append(automation_id)

        async with global_view_workflow_util.global_view_functional_environment(
            tmp_path,
            sim_ticker_close_by_symbol={"BTC/USDT": 9000.0},
        ) as environment:
            user_id = environment["user_id"]
            global_view_workflow_util.seed_account_trading_state(
                environment["trading_provider"],
                user_id,
                account_id=global_view_workflow_util.ACCOUNT_SIM_1_ID,
                seeded_orders=[
                    {
                        "exchange_id": global_view_workflow_util.ORDER_FILL_ID,
                        "price": 10000.0,
                        "trigger_above": False,
                    },
                    {
                        "exchange_id": global_view_workflow_util.ORDER_STAYS_OPEN_ID,
                        "price": 8000.0,
                        "trigger_above": False,
                    },
                ],
            )
            with (
                mock.patch.object(
                    scheduler_api_module,
                    "get_automation_states",
                    mock.AsyncMock(return_value=[matching_automation, non_matching_automation]),
                ),
                mock.patch.object(
                    scheduler_tasks_module,
                    "send_forced_trigger_to_active_automation",
                    side_effect=record_forced_trigger,
                ),
            ):
                workflow_result = await asyncio.wait_for(
                    global_view_workflow_util.enqueue_and_await_global_view_refresh(),
                    timeout=global_view_workflow_util.WORKFLOW_RESULT_TIMEOUT_SECONDS,
                )

            assert workflow_result["refreshed_accounts"] == 3
            assert trigger_calls == [global_view_workflow_util.AUTOMATION_FILL_ID]

            account_provider = environment["account_provider"]
            for account_id in (
                global_view_workflow_util.ACCOUNT_REAL_ID,
                global_view_workflow_util.ACCOUNT_SIM_1_ID,
                global_view_workflow_util.ACCOUNT_SIM_2_ID,
            ):
                updated_account = account_provider.get_item(user_id, account_id)
                assert updated_account.assets is not None
