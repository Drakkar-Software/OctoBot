import pytest

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_flow.jobs

from tests.functionnal_tests import current_time, resolved_actions
from tests.functionnal_tests.signals import signals_test_util as signal_test_util
from tests.functionnal_tests.trading_modes_actions.simulator import test_dca_trading_mode_action as dca_test


@pytest.mark.asyncio
class TestSignalBotFirstStartIdleRecallWhenRelevantForContext:
    async def test_first_start_schedules_without_open_trades_interval(self):
        init_action_dict = signal_test_util.init_action()
        after_signal_bot_dump = await signal_test_util.run_signal_bot_bootstrap(init_action_dict)

        signal_test_util.assert_recall_when_relevant_for_context_scheduled_seconds(after_signal_bot_dump, 10)

        dag_actions = after_signal_bot_dump["automation"]["actions_dag"]["actions"]
        assert len(dag_actions) == 2
        assert dag_actions[1]["dsl_script"].startswith("recall_when_relevant_for_context(")
        assert "grid_trading_mode" not in dag_actions[1]["dsl_script"]


@pytest.mark.asyncio
class TestSignalBotRecallRestartsAfterIntervalExpires:
    async def test_recall_schedules_next_interval_after_wait_expires(self):
        init_action_dict = signal_test_util.init_action()
        after_signal_bot_dump = await signal_test_util.run_signal_bot_bootstrap(init_action_dict)
        signal_test_util.assert_recall_when_relevant_for_context_scheduled_seconds(after_signal_bot_dump, 10)

        expired_recall_time = current_time + 11.0
        _, after_expired_recall_dump, recall_executed_actions = await signal_test_util.run_automation_job_on_dump(
            after_signal_bot_dump,
            execution_time=expired_recall_time,
        )
        assert recall_executed_actions
        signal_test_util.assert_recall_when_relevant_for_context_scheduled_seconds(
            after_expired_recall_dump,
            10,
            reference_time=expired_recall_time,
        )
        dag_actions = after_expired_recall_dump["automation"]["actions_dag"]["actions"]
        assert dag_actions[1].get("executed_at") is None


@pytest.mark.asyncio
class TestSignalBotFirstStartSignalOrderStopWithoutCancel:
    async def test_first_start_signal_order_stop_without_cancel(self):
        init_action_dict = signal_test_util.init_action()
        after_signal_bot_dump = await signal_test_util.run_signal_bot_bootstrap(init_action_dict)
        signal_test_util.assert_recall_when_relevant_for_context_scheduled_seconds(after_signal_bot_dump, 10)

        limit_buy_action = signal_test_util.limit_buy_below_market_priority_action()
        with signal_test_util.patch_limit_buy_simulator_exchange_prices():
            _, after_buy_dump, _ = await signal_test_util.run_automation_job_on_dump(
                after_signal_bot_dump,
                resolved_actions([limit_buy_action]),
            )

            buy_count, sell_count, _ = signal_test_util.open_order_counts_from_dump(after_buy_dump)
            assert buy_count + sell_count >= 1
            first_open_order = after_buy_dump["automation"]["exchange_account_elements"]["orders"]["open_orders"][0]
            order_origin = first_open_order.get(trading_constants.STORAGE_ORIGIN_VALUE, first_open_order)
            assert order_origin.get(trading_enums.ExchangeConstantsOrderColumns.TYPE.value) is not None
            dag_actions = after_buy_dump["automation"]["actions_dag"]["actions"]
            assert dag_actions[0].get("executed_at") is not None
            assert dag_actions[1].get("executed_at") is None
            baseline_buy_count = buy_count
            baseline_sell_count = sell_count

            before_recall_scheduled_to = after_buy_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
            automation_job, after_recall_when_relevant_for_context_dump, recall_executed_actions = await signal_test_util.run_automation_job_on_dump(after_buy_dump)
            assert recall_executed_actions
            signal_test_util.assert_recall_when_relevant_for_context_scheduled_seconds(after_recall_when_relevant_for_context_dump, 5)

            stop_action = signal_test_util.stop_automation_priority_action(cancel_orders=False)
            automation_job, after_stop_dump, _ = await signal_test_util.run_automation_job_on_dump(
                after_recall_when_relevant_for_context_dump,
                resolved_actions([stop_action]),
            )
            assert automation_job.automation_state.automation.post_actions.stop_automation is True
            final_buy_count, final_sell_count, _ = signal_test_util.open_order_counts_from_dump(after_stop_dump)
            assert final_buy_count == baseline_buy_count
            assert final_sell_count == baseline_sell_count


@pytest.mark.asyncio
class TestSignalBotRestartCrossSymbolChainsStopWithCancel:
    async def test_restart_with_existing_orders_cross_symbol_chains_stop_with_cancel(self):
        init_action_dict = signal_test_util.init_action()
        init_action_dict["config"]["automation"]["exchange_account_elements"]["portfolio"]["content"]["USDC"] = {
            "available": 10000.0,
            "total": 10000.0,
        }
        after_signal_bot_dump = await signal_test_util.run_signal_bot_bootstrap(init_action_dict)

        limit_buy_action = signal_test_util.limit_buy_below_market_priority_action()
        with signal_test_util.patch_cross_symbol_simulator_exchange_prices():
            _, after_buy_dump, _ = await signal_test_util.run_automation_job_on_dump(
                after_signal_bot_dump,
                resolved_actions([limit_buy_action]),
            )

        baseline_buy_count, baseline_sell_count, _ = signal_test_util.open_order_counts_from_dump(after_buy_dump)
        assert baseline_buy_count + baseline_sell_count >= 1

        with signal_test_util.patch_cross_symbol_simulator_exchange_prices():
            _, after_restart_dump, recall_executed_actions = await signal_test_util.run_automation_job_on_dump(after_buy_dump)
            assert recall_executed_actions
            signal_test_util.assert_recall_when_relevant_for_context_scheduled_seconds(after_restart_dump, 5)
            restart_buy_count, restart_sell_count, _ = signal_test_util.open_order_counts_from_dump(after_restart_dump)
            assert restart_buy_count == baseline_buy_count
            assert restart_sell_count == baseline_sell_count

        eth_buy_action = signal_test_util.eth_buy_with_take_profit_priority_action()
        with signal_test_util.patch_cross_symbol_simulator_exchange_prices():
            _, after_eth_dump, _ = await signal_test_util.run_automation_job_on_dump(
                after_restart_dump,
                resolved_actions([eth_buy_action]),
            )

        signal_test_util.assert_open_order_symbols_include(after_eth_dump, {dca_test.ETH_USDC})
        eth_buy_count, eth_sell_count, trade_count = signal_test_util.open_order_counts_from_dump(after_eth_dump)
        assert eth_buy_count >= baseline_buy_count
        assert eth_sell_count >= baseline_sell_count
        assert eth_buy_count + eth_sell_count >= baseline_buy_count + baseline_sell_count
        assert trade_count >= 0

        with signal_test_util.patch_cross_symbol_fill_prices():
            _, after_fill_dump, _ = await signal_test_util.run_automation_job_on_dump(after_eth_dump)

        _, _, trade_count_after_fill = signal_test_util.open_order_counts_from_dump(after_fill_dump)
        assert trade_count_after_fill >= trade_count

        stop_action = signal_test_util.stop_automation_priority_action(cancel_orders=True)
        automation_job, after_stop_dump, _ = await signal_test_util.run_automation_job_on_dump(
            after_fill_dump,
            resolved_actions([stop_action]),
        )
        assert automation_job.automation_state.automation.post_actions.stop_automation is True
        final_buy_count, final_sell_count, _ = signal_test_util.open_order_counts_from_dump(after_stop_dump)
        assert final_buy_count == 0
        assert final_sell_count == 0
