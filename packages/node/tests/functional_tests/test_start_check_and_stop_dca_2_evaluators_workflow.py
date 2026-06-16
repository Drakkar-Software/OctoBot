#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import asyncio
import time
import typing

import dbos
import mock
import pytest

import octobot_commons.dsl_interpreter as dsl_interpreter_module
import octobot_protocol.models as octobot_protocol_models

import tentacles.Evaluator.Strategies.mixed_strategies_evaluator.mixed_strategies as mixed_strategies_evaluator
import tentacles.Evaluator.TA.momentum_evaluator.momentum as momentum_evaluator
import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading

from .util import dag_assertions as dag_assertions_module
from .util import dca_workflow as dca_sim_util
from .util import price_mocks as price_mocks_module
from .util import protocol_assertions as protocol_assertions_module
from .util import user_action_assertions as user_action_assertions_module
from .util import workflow_common as workflow_common_module

import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
import octobot_node.scheduler.workflows_util as workflows_util_module
import octobot_trading.enums as trading_enums_module

from tests.scheduler import temp_dbos_scheduler
from tests.scheduler.user_actions.user_actions_executor.util import trading_tentacles_test_utils


_T_ENQUEUE_SECONDS = 5.0
_T_STEP_SECONDS = 30.0
_T_SIGNAL_SECONDS = 10.0
_T_STOP_SEND_SECONDS = 5.0
_T_STOP_COMPLETE_SECONDS = 15.0
_POST_STEP_POLL_SECONDS = 0.05

_DCA_ACCOUNT_ID = "functional_dca_2_evaluators_account"
_DCA_AUTOMATION_DISPLAY_NAME = "test_dca_2_evaluators_automation"
_DCA_MID_RUN_PROTOCOL_STATUSES = (
    octobot_protocol_models.WorkflowStatus.RUNNING,
    octobot_protocol_models.WorkflowStatus.COMPLETED,
)
_FUNCTIONAL_TIME_FRAME = dca_sim_util.FUNCTIONAL_MAXIMUM_EVALUATORS_TIME_FRAME
_RSI_ACTION_ID = trading_tentacles_test_utils.tentacle_action_id(
    momentum_evaluator.RSIMomentumEvaluator.get_name()
)
_EMA_ACTION_ID = trading_tentacles_test_utils.tentacle_action_id(
    momentum_evaluator.EMAMomentumEvaluator.get_name()
)
_STRATEGY_ACTION_ID = trading_tentacles_test_utils.tentacle_action_id(
    mixed_strategies_evaluator.SimpleStrategyEvaluator.get_name()
)
_DCA_ACTION_ID = trading_tentacles_test_utils.tentacle_action_id(
    dca_trading.DCATradingMode.get_name()
)


class TestTriggerTaskDCATwoEvaluatorsDbosIntegration:
    @pytest.mark.asyncio
    async def test_trigger_task_dca_two_evaluators_selective_entry_fill_then_stop(
        self,
        temp_dbos_scheduler,
    ):
        """
        End-to-end maximum-evaluators DCA on BTC/USDC + ETH/USDC with RSI + EMA + strategy.

        Cycle 1: BTC buy signal only → 2 BTC entry orders.
        Cycle 2: no buy signal, BTC fill before strategy → chained sell, DCA does nothing.
        Stop automation cleanly.
        """
        # Build declining-then-fixed OHLCV mocks so evaluators see buy signals on BTC only.
        close_by_symbol = dca_sim_util.default_close_prices_by_symbol()
        ohlcv_fetch_mode = {"use_declining_for_history": True}

        def _decline_per_candle(symbol: str) -> float:
            if symbol == dca_sim_util.BTC_USDC:
                return close_by_symbol[symbol] * 0.005
            return 0.0

        declining_ohlcv = price_mocks_module.fetch_ohlcv_side_effect_for_declining_closes(
            lambda symbol: close_by_symbol[symbol],
            _decline_per_candle,
        )
        fixed_close_ohlcv = price_mocks_module.fetch_ohlcv_side_effect_for_close_prices(
            lambda symbol: close_by_symbol[symbol],
        )
        patched_fetch_ohlcv = price_mocks_module.patched_fetch_ohlcv_with_mode_toggle(
            declining_fetch_ohlcv=declining_ohlcv,
            fixed_close_fetch_ohlcv=fixed_close_ohlcv,
            ohlcv_fetch_mode=ohlcv_fetch_mode,
        )
        patched_fetch_tickers = dca_sim_util.tickers_repository_fetch_tickers_close_override(
            lambda symbol: close_by_symbol[symbol]
        )

        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        protocol_account = workflow_common_module.protocol_account_for_functional(
            account_id=_DCA_ACCOUNT_ID,
            usdc_total=1000.0,
            account_name="Start/stop functional DCA 2-evaluators account",
        )
        create_user_action = dca_sim_util.build_create_dca_user_action(
            account_id=_DCA_ACCOUNT_ID,
            name=_DCA_AUTOMATION_DISPLAY_NAME,
            strategy_id=dca_sim_util.SIMULATOR_DCA_DEFAULT_STRATEGY_ID,
        )

        # Patch market data and providers, then create the maximum-evaluators DCA automation.
        with (
            mock.patch.object(
                octobot_flow_repositories_exchange_module.TickersRepository,
                "fetch_tickers",
                new=patched_fetch_tickers,
            ),
            mock.patch.object(
                octobot_flow_repositories_exchange_module.OhlcvRepository,
                "fetch_ohlcv",
                side_effect=patched_fetch_ohlcv,
            ),
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountProvider.instance",
                return_value=mock.Mock(
                    get_item=mock.Mock(return_value=protocol_account),
                    get_exchange_config=mock.Mock(
                        return_value=workflow_common_module.protocol_exchange_config_for_grid_functional(),
                    ),
                ),
            ),
            mock.patch(
                "octobot_sync.sync.collection_providers.StrategyProvider.instance",
                return_value=mock.Mock(
                    get_item=mock.Mock(
                        return_value=dca_sim_util.seeded_dca_strategy_for_functional_wallet_with_evaluators(
                            stored_strategy_id=dca_sim_util.SIMULATOR_DCA_DEFAULT_STRATEGY_ID,
                        ),
                    ),
                ),
            ),
        ):
            try:
                await asyncio.wait_for(
                    workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                        temp_dbos_scheduler,
                        create_user_action,
                        user_id,
                    ),
                    timeout=_T_ENQUEUE_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("execute_user_action timed out enqueueing automation workflow") from exc

            await user_action_assertions_module.assert_user_action_selector_completed_automation_create(
                user_id=user_id,
                user_action_id=create_user_action.id,
                expected_workflow_id=None,
            )

            metadata_automation_id = user_action_assertions_module.resolve_create_automation_metadata_id(
                create_user_action,
            )
            parent_automation_id = await user_action_assertions_module.get_created_automation_id_from_user_action(
                user_action_id=create_user_action.id,
                user_id=user_id,
            )

            # Helper to enqueue a forced trigger and wait for the signal user action to complete.
            async def _forced_trigger(user_action_id: str) -> None:
                signal_user_action = await workflow_common_module.enqueue_forced_trigger_and_await(
                    temp_dbos_scheduler,
                    automation_id=parent_automation_id,
                    user_id=user_id,
                    user_action_id=user_action_id,
                    timeout_seconds=_T_SIGNAL_SECONDS,
                )
                await user_action_assertions_module.assert_user_action_selector_completed_automation_signal(
                    user_id=user_id,
                    user_action_id=signal_user_action.id,
                )

            # Cycle 1 — evaluators: RSI/EMA complete with BTC buy signal, ETH neutral.
            after_evaluators_workflow = await dag_assertions_module.wait_for_dag_snapshot(
                temp_dbos_scheduler,
                metadata_automation_id,
                {
                    "action_init": {
                        "completed": True,
                        "result_is_none": True,
                        "previous_result_is_none": True,
                    },
                    _RSI_ACTION_ID: {
                        "completed": True,
                        "result_is_none": False,
                        "previous_result_is_none": True,
                    },
                    _EMA_ACTION_ID: {
                        "completed": True,
                        "result_is_none": False,
                        "previous_result_is_none": True,
                    },
                    _STRATEGY_ACTION_ID: {
                        "completed": False,
                        "result_is_none": True,
                        "previous_result_is_none": True,
                    },
                    _DCA_ACTION_ID: {
                        "completed": False,
                        "result_is_none": True,
                        "previous_result_is_none": True,
                    },
                },
                timeout_seconds=_T_STEP_SECONDS,
            )
            after_evaluators_dag = dag_assertions_module.actions_dag_from_workflow_row(
                after_evaluators_workflow
            )
            assert after_evaluators_dag is not None
            dag_assertions_module.assert_evaluator_results_for_symbols(
                after_evaluators_dag.get_actions_by_id()[_RSI_ACTION_ID],
                eval_note_by_symbol={
                    dca_sim_util.BTC_USDC: -1,
                    dca_sim_util.ETH_USDC: 0,
                },
                evaluator_name=momentum_evaluator.RSIMomentumEvaluator.get_name(),
                time_frame=_FUNCTIONAL_TIME_FRAME,
            )
            dag_assertions_module.assert_evaluator_results_for_symbols(
                after_evaluators_dag.get_actions_by_id()[_EMA_ACTION_ID],
                eval_note_by_symbol={
                    dca_sim_util.BTC_USDC: -1,
                    dca_sim_util.ETH_USDC: 0,
                },
                evaluator_name=momentum_evaluator.EMAMomentumEvaluator.get_name(),
                time_frame=_FUNCTIONAL_TIME_FRAME,
            )
            assert {action.id for action in after_evaluators_dag.get_executable_actions()} == {
                _STRATEGY_ACTION_ID
            }

            # Cycle 1 — strategy: aggregate evaluator signals without placing orders yet.
            # DCA entry pricing uses OHLCV limit=1; switch off declining history after evaluators.
            ohlcv_fetch_mode["use_declining_for_history"] = False

            after_strategy_workflow = await dag_assertions_module.wait_for_dag_snapshot(
                temp_dbos_scheduler,
                metadata_automation_id,
                {
                    _STRATEGY_ACTION_ID: {
                        "completed": True,
                        "result_is_none": False,
                        "previous_result_is_none": True,
                    },
                    _DCA_ACTION_ID: {
                        "completed": False,
                        "result_is_none": True,
                        "previous_result_is_none": True,
                    },
                },
                timeout_seconds=_T_STEP_SECONDS,
            )
            after_strategy_reader = workflows_util_module.get_automation_state_reader(
                after_strategy_workflow
            )
            assert after_strategy_reader is not None
            strategy_buys, strategy_sells, strategy_trades = (
                workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                    after_strategy_reader.state.automation.exchange_account_elements
                )
            )
            assert strategy_buys == 0 and strategy_sells == 0 and strategy_trades == 0

            # Cycle 1 — DCA: first run schedules re-call; evaluators/strategy reset for next layer.
            after_dca_workflow = await dag_assertions_module.wait_for_dag_snapshot(
                temp_dbos_scheduler,
                metadata_automation_id,
                {
                    _DCA_ACTION_ID: {
                        "completed": False,
                        "result_is_none": True,
                        "previous_result_is_none": False,
                    },
                    _RSI_ACTION_ID: {
                        "completed": False,
                        "result_is_none": True,
                        "previous_result_is_none": False,
                    },
                    _EMA_ACTION_ID: {
                        "completed": False,
                        "result_is_none": True,
                        "previous_result_is_none": False,
                    },
                    _STRATEGY_ACTION_ID: {
                        "completed": False,
                        "result_is_none": True,
                        "previous_result_is_none": False,
                    },
                },
                timeout_seconds=_T_STEP_SECONDS,
            )
            after_dca_dag = dag_assertions_module.actions_dag_from_workflow_row(after_dca_workflow)
            assert after_dca_dag is not None
            dca_action = after_dca_dag.get_actions_by_id()[_DCA_ACTION_ID]
            assert isinstance(dca_action.previous_execution_result, dict)
            assert dsl_interpreter_module.ReCallingOperatorResult.is_re_calling_operator_result(
                dca_action.previous_execution_result
            )
            assert {action.id for action in after_dca_dag.get_executable_actions()} == {
                _RSI_ACTION_ID,
                _EMA_ACTION_ID,
            }

            # Cycle 1 — poll until DCA places two BTC entry orders and no ETH orders.
            btc_only_deadline = time.monotonic() + _T_STEP_SECONDS
            workflow_row_after_cycle1_dca: typing.Any = None
            elements_after_cycle1_dca: typing.Any = None
            last_btc_counts: dict[str, int] | None = None
            last_eth_counts: dict[str, int] | None = None
            last_trade_count: int | None = None
            while time.monotonic() < btc_only_deadline:
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async():
                    if workflows_util_module.get_automation_id(workflow_row) != metadata_automation_id:
                        continue
                    reader_after_cycle1 = workflows_util_module.get_automation_state_reader(workflow_row)
                    if reader_after_cycle1 is None:
                        continue
                    candidate_elements = reader_after_cycle1.state.automation.exchange_account_elements
                    _, candidate_sells, candidate_trades = (
                        workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                            candidate_elements
                        )
                    )
                    open_orders = dca_sim_util.open_order_origins_from_exchange_elements(candidate_elements)
                    btc_counts = dca_sim_util.count_open_orders_for_symbol(
                        open_orders,
                        dca_sim_util.BTC_USDC,
                    )
                    eth_counts = dca_sim_util.count_open_orders_for_symbol(
                        open_orders,
                        dca_sim_util.ETH_USDC,
                    )
                    last_btc_counts = btc_counts
                    last_eth_counts = eth_counts
                    last_trade_count = candidate_trades
                    if (
                        btc_counts["buy"] == 2
                        and eth_counts["buy"] == 0
                        and candidate_sells == 0
                        and candidate_trades == 0
                    ):
                        workflow_row_after_cycle1_dca = workflow_row
                        elements_after_cycle1_dca = candidate_elements
                        break
                if workflow_row_after_cycle1_dca is not None:
                    break
                await asyncio.sleep(_POST_STEP_POLL_SECONDS)
            else:
                pytest.fail(
                    "Timed out waiting for BTC-only DCA entry baseline "
                    f"(wanted 2 BTC buys, 0 ETH buys, 0 sells, 0 trades; "
                    f"last btc={last_btc_counts!r}, eth={last_eth_counts!r}, trades={last_trade_count!r})"
                )

            open_orders_after_cycle1 = dca_sim_util.open_order_origins_from_exchange_elements(
                elements_after_cycle1_dca
            )
            dca_sim_util.assert_open_buy_ladder_for_symbol(
                open_orders_after_cycle1,
                symbol=dca_sim_util.BTC_USDC,
                close=close_by_symbol[dca_sim_util.BTC_USDC],
            )

            # Cycle 2 — lower close so the deepest BTC buy limit fills before strategy runs.
            ohlcv_fetch_mode["use_declining_for_history"] = False
            btc_buy_orders_after_cycle1 = dca_sim_util.sorted_orders_by_side_and_symbol(
                open_orders_after_cycle1,
                trading_enums_module.TradeOrderSide.BUY.value,
                dca_sim_util.BTC_USDC,
            )
            highest_btc_buy_order = btc_buy_orders_after_cycle1[-1]
            dca_sim_util.drop_close_below_order_price(close_by_symbol, highest_btc_buy_order)

            # Cycle 2 — evaluators re-run with neutral signals (no new buy intent).
            await _forced_trigger("ua-signal-dca-2eval-cycle2-evaluators")
            await dag_assertions_module.wait_for_dag_snapshot(
                temp_dbos_scheduler,
                metadata_automation_id,
                {
                    _RSI_ACTION_ID: {
                        "completed": True,
                        "result_is_none": False,
                        "previous_result_is_none": False,
                    },
                    _EMA_ACTION_ID: {
                        "completed": True,
                        "result_is_none": False,
                        "previous_result_is_none": False,
                    },
                    _STRATEGY_ACTION_ID: {
                        "completed": False,
                        "result_is_none": True,
                        "previous_result_is_none": False,
                    },
                },
                timeout_seconds=_T_STEP_SECONDS,
            )

            buys_before_cycle2_strategy, sells_before_cycle2_strategy, trades_before_cycle2_strategy = (
                workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                    elements_after_cycle1_dca
                )
            )
            assert buys_before_cycle2_strategy == 2
            assert sells_before_cycle2_strategy == 0
            assert trades_before_cycle2_strategy == 0

            # Cycle 2 — strategy after fill: chained sell on BTC, still no ETH exposure.
            cycle2_strategy_deadline = time.monotonic() + _T_STEP_SECONDS
            elements_after_cycle2_strategy: typing.Any = None

            async def _poll_cycle2_post_fill_state() -> bool:
                nonlocal elements_after_cycle2_strategy
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async():
                    if workflows_util_module.get_automation_id(workflow_row) != metadata_automation_id:
                        continue
                    reader_after_cycle2 = workflows_util_module.get_automation_state_reader(workflow_row)
                    if reader_after_cycle2 is None:
                        continue
                    candidate_elements = reader_after_cycle2.state.automation.exchange_account_elements
                    _, candidate_sells, candidate_trades = (
                        workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                            candidate_elements
                        )
                    )
                    open_orders = dca_sim_util.open_order_origins_from_exchange_elements(
                        candidate_elements
                    )
                    if not dca_sim_util.is_cycle2_after_lowest_btc_buy_fill(open_orders):
                        continue
                    elements_after_cycle2_strategy = candidate_elements
                    return True
                return False

            if not await _poll_cycle2_post_fill_state():
                await _forced_trigger("ua-signal-dca-2eval-cycle2-strategy")

            while time.monotonic() < cycle2_strategy_deadline:
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async():
                    if workflows_util_module.get_automation_id(workflow_row) != metadata_automation_id:
                        continue
                    reader_after_cycle2_strategy = workflows_util_module.get_automation_state_reader(
                        workflow_row
                    )
                    if reader_after_cycle2_strategy is None:
                        continue
                    candidate_elements = (
                        reader_after_cycle2_strategy.state.automation.exchange_account_elements
                    )
                    _, candidate_sells, candidate_trades = (
                        workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                            candidate_elements
                        )
                    )
                    open_orders = dca_sim_util.open_order_origins_from_exchange_elements(
                        candidate_elements
                    )
                    if not dca_sim_util.is_cycle2_after_lowest_btc_buy_fill(open_orders):
                        continue
                    elements_after_cycle2_strategy = candidate_elements
                    break
                if elements_after_cycle2_strategy is not None:
                    break
                await asyncio.sleep(_POST_STEP_POLL_SECONDS)
            else:
                pytest.fail(
                    "Timed out waiting for cycle-2 strategy fill (>=1 buy, >=1 sell, >=1 trade)"
                )

            open_orders_after_cycle2_strategy = dca_sim_util.open_order_origins_from_exchange_elements(
                elements_after_cycle2_strategy
            )
            btc_counts_after_strategy = dca_sim_util.count_open_orders_for_symbol(
                open_orders_after_cycle2_strategy,
                dca_sim_util.BTC_USDC,
            )
            assert btc_counts_after_strategy["buy"] >= 1
            assert btc_counts_after_strategy["sell"] >= 1
            assert (
                dca_sim_util.count_open_orders_for_symbol(
                    open_orders_after_cycle2_strategy,
                    dca_sim_util.ETH_USDC,
                )["buy"]
                == 0
            )

            buys_before_cycle2_dca, sells_before_cycle2_dca, _ = (
                workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                    elements_after_cycle2_strategy
                )
            )

            # Cycle 2 — DCA step is a no-op when strategy signals do not request new entries.
            await _forced_trigger("ua-signal-dca-2eval-cycle2-dca")
            cycle2_dca_deadline = time.monotonic() + _T_STEP_SECONDS
            elements_after_cycle2_dca: typing.Any = None
            while time.monotonic() < cycle2_dca_deadline:
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async():
                    if workflows_util_module.get_automation_id(workflow_row) != metadata_automation_id:
                        continue
                    reader_after_cycle2_dca = workflows_util_module.get_automation_state_reader(
                        workflow_row
                    )
                    if reader_after_cycle2_dca is None:
                        continue
                    candidate_elements = reader_after_cycle2_dca.state.automation.exchange_account_elements
                    candidate_buys, candidate_sells, candidate_trades = (
                        workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                            candidate_elements
                        )
                    )
                    if (
                        candidate_buys != buys_before_cycle2_dca
                        or candidate_sells != sells_before_cycle2_dca
                    ):
                        continue
                    elements_after_cycle2_dca = candidate_elements
                    break
                if elements_after_cycle2_dca is not None:
                    break
                await asyncio.sleep(_POST_STEP_POLL_SECONDS)
            else:
                pytest.fail("Timed out waiting for cycle-2 DCA step to leave orders unchanged")

            open_orders_after_cycle2_dca = dca_sim_util.open_order_origins_from_exchange_elements(
                elements_after_cycle2_dca
            )
            assert dca_sim_util.count_open_orders_for_symbol(
                open_orders_after_cycle2_dca,
                dca_sim_util.BTC_USDC,
            ) == dca_sim_util.count_open_orders_for_symbol(
                open_orders_after_cycle2_strategy,
                dca_sim_util.BTC_USDC,
            )

            # Stop the automation and assert terminal workflow output plus protocol state.
            stop_user_action = workflow_common_module.build_stop_user_action(
                automation_id=parent_automation_id,
                user_action_id="ua-stop-dca-2eval-functional",
            )
            try:
                await asyncio.wait_for(
                    workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                        temp_dbos_scheduler,
                        stop_user_action,
                        user_id,
                    ),
                    timeout=_T_STOP_SEND_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("execute_user_action stop timed out") from exc

            await user_action_assertions_module.assert_user_action_selector_completed_automation_stop(
                user_id=user_id,
                user_action_id=stop_user_action.id,
            )

            final_output_text = await workflow_common_module.wait_for_stop_success_output(
                temp_dbos_scheduler,
                metadata_automation_id,
                _T_STOP_COMPLETE_SECONDS,
            )
            assert final_output_text is not None
            parsed_final = workflow_common_module.parse_automation_workflow_output(final_output_text)
            assert parsed_final.error is None
            final_job = workflow_common_module.job_description_dict_from_output(parsed_final)
            final_automation = final_job["state"]["automation"]
            assert final_automation["post_actions"]["stop_automation"] is True
            final_elements = final_automation["exchange_account_elements"]
            final_buys, final_sells, final_trades = (
                workflow_common_module.buy_sell_trade_counts_from_exchange_elements(final_elements)
            )
            assert dca_sim_util.is_cycle2_post_fill_state(final_buys, final_sells, final_trades)

            success_rows = [
                workflow_row
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                if workflow_row.status == dbos.WorkflowStatusString.SUCCESS.value
                and workflows_util_module.get_automation_id(workflow_row) == metadata_automation_id
            ]
            assert success_rows
            final_workflow_row = max(success_rows, key=lambda workflow_status: workflow_status.updated_at or 0)
            protocol_state_final = await workflow_common_module.load_protocol_automation_state_for_workflow(
                user_id,
                final_workflow_row,
            )
            protocol_assertions_module.assert_protocol_automation_matches_exchange_account_elements_multi_symbol(
                protocol_state_final,
                final_elements,
                expected_automation_task_status=octobot_protocol_models.WorkflowStatus.COMPLETED,
                expected_exchange_account_id=_DCA_ACCOUNT_ID,
                allowed_order_symbols=dca_sim_util.TRADED_SYMBOLS,
            )
            protocol_assertions_module.assert_protocol_automation_metadata_name(
                protocol_state_final,
                _DCA_AUTOMATION_DISPLAY_NAME,
            )
