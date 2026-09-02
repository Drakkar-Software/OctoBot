import mock
import time

import pytest

import octobot_flow.enums as flow_enums
import octobot_flow.jobs

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import current_time, resolved_actions
from tests.functionnal_tests.signals import signals_test_util as signal_test_util


@pytest.mark.asyncio
class TestPrioritySignalBuyCreatesOrder:
    async def test_buy_creates_open_order(self):
        # 1. Bootstrap automation via init action (USDC portfolio + exchange context)
        init_action_dict = signal_test_util.init_action()
        after_init_dump = await signal_test_util.run_init_only(init_action_dict)
        # 2. Resolve signal buy keyval to DSL and build priority action batch
        buy_dsl = signal_test_util.resolved_signal_dsl(
            "SYMBOL=BTC/USDC\nSIGNAL=buy\nVOLUME=0.01",
        )
        priority_actions = resolved_actions(
            [signal_test_util.priority_action("priority_buy", buy_dsl)],
        )
        with (
            functionnal_tests.mocked_community_authentication(),
            functionnal_tests.mocked_community_repository(),
            mock.patch.object(time, "time", return_value=current_time),
        ):
            # 3. Run AutomationJob with priority actions on dumped state
            async with octobot_flow.jobs.AutomationJob(
                after_init_dump,
                priority_actions,
                [],
                {},
            ) as automation_job:
                await automation_job.run()

            # 4. Assert buy side-effect and priority action historized
            portfolio_content = automation_job.dump()["automation"]["exchange_account_elements"]["portfolio"]["content"]
            assert "BTC" in portfolio_content or portfolio_content["USDC"]["total"] < 1000.0
            signal_test_util.assert_historized_priority_actions(
                automation_job.automation_state,
                priority_actions,
                executed_at_min=current_time,
            )


@pytest.mark.asyncio
class TestPrioritySignalCancelCancelsOrders:
    async def test_cancel_clears_orders(self):
        # 1. Bootstrap grid so open buy/sell orders exist
        init_action_dict = signal_test_util.init_action()
        after_grid_dump = await signal_test_util.run_simulator_grid_bootstrap(init_action_dict)
        # 2. Assert baseline open orders before cancel
        buy_count, sell_count, _trade_count = signal_test_util.open_order_counts_from_dump(after_grid_dump)
        assert buy_count >= 1
        assert sell_count >= 1

        # 3. Resolve signal cancel and run as priority action
        cancel_dsl = signal_test_util.resolved_signal_dsl("SYMBOL=BTC/USDC\nSIGNAL=cancel")
        priority_actions = resolved_actions(
            [signal_test_util.priority_action("priority_cancel", cancel_dsl)],
        )
        with (
            functionnal_tests.mocked_community_authentication(),
            functionnal_tests.mocked_community_repository(),
            mock.patch.object(time, "time", return_value=current_time),
        ):
            async with octobot_flow.jobs.AutomationJob(
                after_grid_dump,
                priority_actions,
                [],
                {},
            ) as automation_job:
                await automation_job.run()

            # 4. Assert all open orders cleared and priority action historized
            final_buy_count, final_sell_count, _ = signal_test_util.open_order_counts_from_dump(
                automation_job.dump(),
            )
            assert final_buy_count == 0
            assert final_sell_count == 0
            signal_test_util.assert_historized_priority_actions(
                automation_job.automation_state,
                priority_actions,
                executed_at_min=current_time,
            )


@pytest.mark.asyncio
class TestPriorityRunsBeforeDag:
    async def test_priority_executes_before_wait_dag(self):
        init_action_dict = signal_test_util.init_action()
        wait_action = {
            "id": "action_wait",
            "dsl_script": "wait(min_delay=1.0, max_delay=1.0)",
            "dependencies": [{"action_id": init_action_dict["id"]}],
        }
        with (
            functionnal_tests.mocked_community_authentication(),
            functionnal_tests.mocked_community_repository(),
            mock.patch.object(time, "time", return_value=current_time),
        ):
            # 1. Init automation with a pending wait DAG action (not yet executed)
            automation_state = functionnal_tests.automation_state_dict(
                resolved_actions([init_action_dict, wait_action]),
            )
            async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as init_automation_job:
                await init_automation_job.run()
            assert init_automation_job.automation_state.automation.actions_dag.actions[1].executed_at is None

            # 2. Inject stop_automation() priority action on dumped state
            stop_dsl = "stop_automation()"
            priority_actions = resolved_actions(
                [signal_test_util.priority_action("priority_stop", stop_dsl)],
            )
            async with octobot_flow.jobs.AutomationJob(
                init_automation_job.dump(),
                priority_actions,
                [],
                {},
            ) as automation_job:
                await automation_job.run()

            # 3. Assert priority historized, wait DAG still pending, and stop flag set
            signal_test_util.assert_historized_priority_actions(
                automation_job.automation_state,
                priority_actions,
                executed_at_min=current_time,
            )
            assert automation_job.automation_state.automation.actions_dag.actions[1].executed_at is None
            assert automation_job.automation_state.automation.post_actions.stop_automation is True


@pytest.mark.asyncio
class TestPriorityMultipleActionsInOneBatch:
    async def test_two_actions_executed_in_order(self):
        # 1. Bootstrap via init (market buy fills; cancel then has no open orders to match)
        init_action_dict = signal_test_util.init_action()
        after_init_dump = await signal_test_util.run_init_only(init_action_dict)
        # 2. Build two priority actions (buy then cancel) in one batch
        buy_dsl = signal_test_util.resolved_signal_dsl(
            "SYMBOL=BTC/USDC\nSIGNAL=buy\nVOLUME=0.01",
        )
        cancel_dsl = signal_test_util.resolved_signal_dsl("SYMBOL=BTC/USDC\nSIGNAL=cancel")
        priority_actions = resolved_actions(
            [
                signal_test_util.priority_action("priority_buy", buy_dsl),
                signal_test_util.priority_action("priority_cancel", cancel_dsl),
            ],
        )
        with (
            functionnal_tests.mocked_community_authentication(),
            functionnal_tests.mocked_community_repository(),
            mock.patch.object(time, "time", return_value=current_time),
        ):
            async with octobot_flow.jobs.AutomationJob(
                after_init_dump,
                priority_actions,
                [],
                {},
            ) as automation_job:
                await automation_job.run()

            # 3. Assert both historized; buy succeeds, cancel fails with no matching orders
            signal_test_util.assert_historized_priority_actions(
                automation_job.automation_state,
                priority_actions,
                executed_at_min=current_time,
                expected_by_id={
                    "priority_cancel": {
                        "error_status": flow_enums.ActionErrorStatus.ORDER_NOT_FOUND.value,
                        "error_message": (
                            f"No [{functionnal_tests.EXCHANGE_INTERNAL_NAME}] order found matching "
                            "{'symbol': 'BTC/USDC'}"
                        ),
                        "result_is_none": True,
                    },
                },
            )
            final_buy_count, final_sell_count, _ = signal_test_util.open_order_counts_from_dump(
                automation_job.dump(),
            )
            assert final_buy_count == 0
            assert final_sell_count == 0


@pytest.mark.asyncio
class TestPrioritySignalFailureHistorized:
    async def test_failing_priority_action_records_error_on_state(self):
        # 1. Bootstrap via init
        init_action_dict = signal_test_util.init_action()
        after_init_dump = await signal_test_util.run_init_only(init_action_dict)
        # 2. Build failing priority action via error() DSL
        failing_dsl = "error('not_enough_funds', 'Priority signal buy rejected')"
        priority_actions = resolved_actions(
            [signal_test_util.priority_action("priority_fail", failing_dsl)],
        )
        with (
            functionnal_tests.mocked_community_authentication(),
            functionnal_tests.mocked_community_repository(),
            mock.patch.object(time, "time", return_value=current_time),
        ):
            async with octobot_flow.jobs.AutomationJob(
                after_init_dump,
                priority_actions,
                [],
                {},
            ) as automation_job:
                await automation_job.run()

            # 3. Assert failure historized on automation state
            signal_test_util.assert_historized_priority_actions(
                automation_job.automation_state,
                priority_actions,
                executed_at_min=current_time,
                expected_by_id={
                    "priority_fail": {
                        "error_status": flow_enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value,
                        "error_message": "Priority signal buy rejected",
                        "result_is_none": True,
                    },
                },
            )
            # 4. Sanity: no trading side-effect
            portfolio_content = automation_job.dump()["automation"]["exchange_account_elements"]["portfolio"]["content"]
            assert portfolio_content["USDC"]["total"] == 1000.0


@pytest.mark.xfail(
    reason="ETH/USDC priority trading on BTC/USDC-only grid not enabled yet; see follow-up plan",
    strict=False,
)
@pytest.mark.asyncio
class TestPrioritySignalCrossSymbolGridDraft:
    async def test_eth_usdc_buy_on_btc_usdc_grid_historized(self):
        # Draft: cross-pair signal priority on a single-pair grid automation.
        # Follow-up plan must enable non-config symbols before removing xfail.
        # 1. Bootstrap BTC/USDC grid
        init_action_dict = signal_test_util.init_action()
        after_grid_dump = await signal_test_util.run_simulator_grid_bootstrap(init_action_dict)
        baseline_buy_count, baseline_sell_count, _ = signal_test_util.open_order_counts_from_dump(after_grid_dump)
        assert baseline_buy_count >= 1
        assert baseline_sell_count >= 1

        # 2. Resolve ETH/USDC signal buy and run as priority action
        eth_buy_dsl = signal_test_util.resolved_signal_dsl(
            "SYMBOL=ETH/USDC\nSIGNAL=buy\nVOLUME=0.01",
        )
        priority_actions = resolved_actions(
            [signal_test_util.priority_action("priority_eth_buy", eth_buy_dsl)],
        )
        with (
            functionnal_tests.mocked_community_authentication(),
            functionnal_tests.mocked_community_repository(),
            mock.patch.object(time, "time", return_value=current_time),
        ):
            async with octobot_flow.jobs.AutomationJob(
                after_grid_dump,
                priority_actions,
                [],
                {},
            ) as automation_job:
                await automation_job.run()

            # 3. Assert success historization (target behavior once feature lands)
            signal_test_util.assert_historized_priority_actions(
                automation_job.automation_state,
                priority_actions,
                executed_at_min=current_time,
            )

            # 4. Assert ETH/USDC side-effect; BTC/USDC grid orders unchanged
            portfolio_content = automation_job.dump()["automation"]["exchange_account_elements"]["portfolio"]["content"]
            assert "ETH" in portfolio_content or portfolio_content["USDC"]["total"] < 1000.0
            final_buy_count, final_sell_count, _ = signal_test_util.open_order_counts_from_dump(
                automation_job.dump(),
            )
            assert final_buy_count == baseline_buy_count
            assert final_sell_count == baseline_sell_count
