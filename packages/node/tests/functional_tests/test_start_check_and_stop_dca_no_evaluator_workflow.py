#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import asyncio
import decimal
import mock
import time
import typing

import dbos
import pytest

import octobot_protocol.models as octobot_protocol_models

from .util import dca_workflow as dca_sim_util
from .util import authenticator_mocks as authenticator_mocks_module
from .util import price_mocks as price_mocks_module
from .util import protocol_assertions as protocol_assertions_module
from .util import user_action_assertions as user_action_assertions_module
from .util import workflow_common as workflow_common_module

import octobot.community.authentication as community_authentication_module
import octobot_flow.entities as octobot_flow_entities
import octobot_trading.enums as trading_enums_module
import octobot_node.scheduler.workflows_util as workflows_util_module
import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module

from tests.scheduler import temp_dbos_scheduler


_T_ENQUEUE_SECONDS = 5.0
_T_DCA_SECONDS = 30.0
_T_SIGNAL_SECONDS = 10.0
_T_STOP_SEND_SECONDS = 5.0
_T_STOP_COMPLETE_SECONDS = 15.0
_POST_STOP_PROTOCOL_POLL_SECONDS = 0.05

_DCA_ACCOUNT_ID = "functional_dca_account"
_DCA_AUTOMATION_DISPLAY_NAME = "test_dca_no_evaluator_automation"
_DCA_MID_RUN_PROTOCOL_STATUSES = (
    octobot_protocol_models.WorkflowStatus.RUNNING,
    octobot_protocol_models.WorkflowStatus.COMPLETED,
)


class TestTriggerTaskDCANoEvaluatorDbosIntegration:
    @pytest.mark.asyncio
    async def test_trigger_task_dca_simulator_entry_fill_then_stop(self, temp_dbos_scheduler):
        """
        End-to-end DCA automation lifecycle on the simulator exchange (BTC/USDC + ETH/USDC).

        Flow: create automation → wait for 4 buy entry orders → drop prices to fill lowest buys
        on both symbols and re-trigger ladders → stop automation → verify clean termination.
        """
        # Setup — deterministic simulator prices, seeded account/strategy, and create user action.
        close_by_symbol = dca_sim_util.default_close_prices_by_symbol()
        entry_close_by_symbol = dict(close_by_symbol)
        patched_fetch_tickers = dca_sim_util.tickers_repository_fetch_tickers_close_override(
            lambda symbol: close_by_symbol[symbol]
        )
        patched_fetch_ohlcv = price_mocks_module.fetch_ohlcv_side_effect_for_close_prices(
            lambda symbol: close_by_symbol[symbol]
        )
        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        protocol_account = workflow_common_module.protocol_account_for_functional(
            account_id=_DCA_ACCOUNT_ID,
            usdc_total=1000.0,
            account_name="Start/stop functional DCA account",
        )
        create_user_action = dca_sim_util.build_create_dca_user_action(
            account_id=_DCA_ACCOUNT_ID,
            name=_DCA_AUTOMATION_DISPLAY_NAME,
        )

        authentication_instance = authenticator_mocks_module.build_community_authentication(
            workflow_common_module.SIMULATOR_GRID_TEST_PRIVATE_KEY,
            workflow_common_module.SIMULATOR_GRID_TEST_WALLET_PASSPHRASE,
        )

        with (
            mock.patch.object(
                community_authentication_module.CommunityAuthentication,
                "instance",
                return_value=authentication_instance,
            ),
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
                        return_value=dca_sim_util.seeded_dca_strategy_for_functional_wallet(
                            stored_strategy_id=dca_sim_util.SIMULATOR_DCA_DEFAULT_STRATEGY_ID,
                        ),
                    ),
                ),
            ),
        ):
            # Step 1 — Enqueue AUTOMATION_CREATE; expect a completed create result and a running workflow.
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

            # Step 2 — Poll until DCA entry baseline: 2 buy ladders per symbol (4 buys), no sells, no trades.
            dca_deadline = time.monotonic() + _T_DCA_SECONDS
            automation_reader_matching: typing.Any = None
            workflow_row_matching: typing.Any = None
            metadata_automation_id = user_action_assertions_module.resolve_create_automation_metadata_id(
                create_user_action,
            )
            while time.monotonic() < dca_deadline:
                workflow_rows = await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                dca_predicate_met = False
                for workflow_row in workflow_rows:
                    workflow_automation_id = workflows_util_module.get_automation_id(workflow_row)
                    if workflow_automation_id != metadata_automation_id:
                        continue
                    state_reader = workflows_util_module.get_automation_state_reader(workflow_row)
                    if state_reader is None:
                        continue
                    elements = state_reader.state.automation.exchange_account_elements
                    buy_orders, sell_orders, trade_bucket = (
                        workflow_common_module.buy_sell_trade_counts_from_exchange_elements(elements)
                    )
                    if dca_sim_util.is_dca_entry_baseline(buy_orders, sell_orders, trade_bucket):
                        automation_reader_matching = state_reader
                        workflow_row_matching = workflow_row
                        dca_predicate_met = True
                        break
                if dca_predicate_met:
                    break
                await asyncio.sleep(workflow_common_module.DEFAULT_WORKFLOW_POLL_INTERVAL_SECONDS)
            else:
                if automation_reader_matching is None:
                    pytest.fail(
                        "Timed out before any readable automation workflow state existed for automation_1"
                    )
                last_buys, last_sells, last_trades = (
                    workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                        automation_reader_matching.state.automation.exchange_account_elements
                    )
                )
                pytest.fail(
                    f"Timed out waiting for DCA entry baseline (wanted 4 buy, 0 sell, 0 trade); "
                    f"last seen buys={last_buys}, sells={last_sells}, trades={last_trades}"
                )

            elems_after_entry = automation_reader_matching.state.automation.exchange_account_elements
            buys_entry, sells_entry, trades_entry = workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                elems_after_entry
            )
            assert dca_sim_util.is_dca_entry_baseline(buys_entry, sells_entry, trades_entry)
            open_orders_after_entry = dca_sim_util.open_order_origins_from_exchange_elements(elems_after_entry)
            for traded_symbol in dca_sim_util.TRADED_SYMBOLS:
                dca_sim_util.assert_open_buy_ladder_for_symbol(
                    open_orders_after_entry,
                    symbol=traded_symbol,
                    close=entry_close_by_symbol[traded_symbol],
                )

            # Step 2 (continued) — Ladder prices match config; protocol AutomationState mirrors exchange elements.
            assert workflow_row_matching is not None
            protocol_state_after_entry = await workflow_common_module.load_protocol_automation_state_for_workflow(
                user_id,
                workflow_row_matching,
            )
            protocol_assertions_module.assert_protocol_automation_matches_exchange_account_elements_multi_symbol(
                protocol_state_after_entry,
                elems_after_entry,
                acceptable_automation_task_statuses=_DCA_MID_RUN_PROTOCOL_STATUSES,
                expected_exchange_account_id=_DCA_ACCOUNT_ID,
                allowed_order_symbols=dca_sim_util.TRADED_SYMBOLS,
            )
            protocol_assertions_module.assert_protocol_automation_metadata_name(
                protocol_state_after_entry,
                _DCA_AUTOMATION_DISPLAY_NAME,
            )

            parent_automation_id = await user_action_assertions_module.get_created_automation_id_from_user_action(
                user_action_id=create_user_action.id,
                user_id=user_id,
            )

            # Step 3 — Fill lowest buy on one symbol, then forced-trigger so the mode re-evaluates at the new close.
            async def _enqueue_forced_trigger_and_await(*, user_action_id: str) -> None:
                signal_user_action = workflow_common_module.build_forced_trigger_signal_user_action(
                    automation_id=parent_automation_id,
                    user_action_id=user_action_id,
                )
                try:
                    await asyncio.wait_for(
                        workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                            temp_dbos_scheduler,
                            signal_user_action,
                            user_id,
                        ),
                        timeout=_T_SIGNAL_SECONDS,
                    )
                except TimeoutError as exc:
                    raise AssertionError("execute_user_action forced-trigger signal timed out") from exc
                await user_action_assertions_module.assert_user_action_selector_completed_automation_signal(
                    user_id=user_id,
                    user_action_id=signal_user_action.id,
                )

            # One symbol at a time: dropping both closes at once would fill every entry buy in a single pass.
            first_fill_order = dca_sim_util.globally_lowest_buy_order(open_orders_after_entry)
            first_fill_symbol = dca_sim_util.drop_close_below_order_price(
                close_by_symbol,
                first_fill_order,
            )
            await _enqueue_forced_trigger_and_await(user_action_id="ua-signal-forced-dca-functional-1")

            # Step 3 (continued) — Wait until at least one buy filled (4 buys still open, >=1 trade).
            partial_fill_deadline = time.monotonic() + _T_DCA_SECONDS
            open_orders_after_first_fill: list[dict] | None = None
            while time.monotonic() < partial_fill_deadline:
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async():
                    if workflows_util_module.get_automation_id(workflow_row) != metadata_automation_id:
                        continue
                    reader_after_first_fill = workflows_util_module.get_automation_state_reader(
                        workflow_row
                    )
                    if reader_after_first_fill is None:
                        continue
                    candidate_elements = reader_after_first_fill.state.automation.exchange_account_elements
                    candidate_buys, candidate_sells, candidate_trades = (
                        workflow_common_module.buy_sell_trade_counts_from_exchange_elements(candidate_elements)
                    )
                    if not dca_sim_util.is_dca_after_symbol_fill_progress(
                        candidate_buys,
                        candidate_sells,
                        candidate_trades,
                    ):
                        continue
                    open_orders_after_first_fill = dca_sim_util.open_order_origins_from_exchange_elements(
                        candidate_elements
                    )
                    break
                if open_orders_after_first_fill is not None:
                    break
                await asyncio.sleep(_POST_STOP_PROTOCOL_POLL_SECONDS)
            else:
                pytest.fail(
                    "Timed out waiting for first DCA symbol fill (wanted 4 buy, >=1 trade)"
                )

            # Restore the first symbol close, then fill the other symbol if it still has no open sell.
            close_by_symbol[first_fill_symbol] = entry_close_by_symbol[first_fill_symbol]
            if not dca_sim_util.both_symbols_have_open_sell_orders(open_orders_after_first_fill):
                remaining_symbols = [
                    traded_symbol
                    for traded_symbol in dca_sim_util.TRADED_SYMBOLS
                    if traded_symbol != first_fill_symbol
                ]
                assert len(remaining_symbols) == 1
                second_fill_symbol = remaining_symbols[0]
                second_symbol_buy_orders = dca_sim_util.sorted_orders_by_side_and_symbol(
                    open_orders_after_first_fill,
                    trading_enums_module.TradeOrderSide.BUY.value,
                    second_fill_symbol,
                )
                assert len(second_symbol_buy_orders) == 2
                second_fill_order = second_symbol_buy_orders[0]
                dca_sim_util.drop_close_below_order_price(close_by_symbol, second_fill_order)
                await _enqueue_forced_trigger_and_await(user_action_id="ua-signal-forced-dca-functional-2")

            # Step 4 — Poll until both symbols re-laddered: 4 buys, >=2 sells, >=2 trades, >=1 sell each.
            fill_deadline = time.monotonic() + _T_DCA_SECONDS
            workflow_row_after_fill: typing.Any = None
            elements_after_fill: typing.Any = None
            while time.monotonic() < fill_deadline:
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async():
                    if workflows_util_module.get_automation_id(workflow_row) != metadata_automation_id:
                        continue
                    reader_after_fill = workflows_util_module.get_automation_state_reader(workflow_row)
                    if reader_after_fill is None:
                        continue
                    candidate_elements = reader_after_fill.state.automation.exchange_account_elements
                    candidate_buys, candidate_sells, candidate_trades = (
                        workflow_common_module.buy_sell_trade_counts_from_exchange_elements(candidate_elements)
                    )
                    if not dca_sim_util.is_dca_after_lowest_buy_fill_and_retrigger(
                        candidate_buys,
                        candidate_sells,
                        candidate_trades,
                    ):
                        continue
                    candidate_open_orders = dca_sim_util.open_order_origins_from_exchange_elements(
                        candidate_elements
                    )
                    if not dca_sim_util.both_symbols_have_open_sell_orders(candidate_open_orders):
                        continue
                    workflow_row_after_fill = workflow_row
                    elements_after_fill = candidate_elements
                    break
                if workflow_row_after_fill is not None:
                    break
                await asyncio.sleep(_POST_STOP_PROTOCOL_POLL_SECONDS)
            else:
                pytest.fail(
                    "Timed out waiting for DCA post-fill state "
                    "(wanted 4 buy, >=2 sell, >=2 trade, >=1 sell per symbol)"
                )

            open_orders_after_fill = dca_sim_util.open_order_origins_from_exchange_elements(elements_after_fill)
            for traded_symbol in dca_sim_util.TRADED_SYMBOLS:
                buy_orders_for_symbol = dca_sim_util.sorted_orders_by_side_and_symbol(
                    open_orders_after_fill,
                    trading_enums_module.TradeOrderSide.BUY.value,
                    traded_symbol,
                )
                assert len(buy_orders_for_symbol) == 2
                sell_orders_for_symbol = dca_sim_util.sorted_orders_by_side_and_symbol(
                    open_orders_after_fill,
                    trading_enums_module.TradeOrderSide.SELL.value,
                    traded_symbol,
                )
                assert len(sell_orders_for_symbol) >= 1

            # Step 4 (continued) — Mid-run protocol state still matches exchange after fills.
            protocol_state_after_fill = await workflow_common_module.load_protocol_automation_state_for_workflow(
                user_id,
                workflow_row_after_fill,
            )
            protocol_assertions_module.assert_protocol_automation_matches_exchange_account_elements_multi_symbol(
                protocol_state_after_fill,
                elements_after_fill,
                acceptable_automation_task_statuses=_DCA_MID_RUN_PROTOCOL_STATUSES,
                expected_exchange_account_id=_DCA_ACCOUNT_ID,
                allowed_order_symbols=dca_sim_util.TRADED_SYMBOLS,
            )

            # Step 5 — Enqueue AUTOMATION_STOP on the parent automation id.
            stop_user_action = workflow_common_module.build_stop_user_action(
                automation_id=parent_automation_id,
                user_action_id="ua-stop-dca-functional",
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

            # Step 6 — Wait for SUCCESS workflow output with post_actions.stop_automation set.
            final_output_text = await workflow_common_module.wait_for_stop_success_output(
                temp_dbos_scheduler,
                metadata_automation_id,
                _T_STOP_COMPLETE_SECONDS,
            )

            assert final_output_text is not None
            parsed_final = workflow_common_module.parse_automation_workflow_output(final_output_text)
            assert parsed_final.error is None
            final_job = workflow_common_module.job_description_dict_from_output(parsed_final)
            assert set(final_job.keys()) == {"auth_details", "state"}
            final_auth_details = octobot_flow_entities.UserAuthentication.from_dict(
                final_job["auth_details"]
            )
            assert final_auth_details.wallet_address == workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS
            final_automation = final_job["state"]["automation"]
            assert final_automation["post_actions"]["stop_automation"] is True
            final_elements = final_automation["exchange_account_elements"]
            final_buys, final_sells, final_trades = workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                final_elements
            )
            assert dca_sim_util.is_dca_after_lowest_buy_fill_and_retrigger(
                final_buys,
                final_sells,
                final_trades,
            )

            # Step 7 — Latest SUCCESS row exposes COMPLETED protocol AutomationState matching final output.
            success_rows = [
                workflow_row
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                if workflow_row.status == dbos.WorkflowStatusString.SUCCESS.value
                and workflows_util_module.get_automation_id(workflow_row) == metadata_automation_id
            ]
            assert success_rows, "expected at least one SUCCESS workflow for automation after stop"
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
