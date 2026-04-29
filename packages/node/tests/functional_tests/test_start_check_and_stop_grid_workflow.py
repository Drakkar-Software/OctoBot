#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import asyncio
import json
import mock
import os
import time
import typing

import dbos
import pytest

import octobot_node.models
import octobot_node.scheduler.tasks

from tests.scheduler import temp_dbos_scheduler


IMPORTED_OCTOBOT_FLOW_GRID_DEPS = False
try:
    import octobot_commons.dsl_interpreter as dsl_interpreter_module
    import octobot_commons.enums as common_enums_module
    import octobot_flow.entities as octobot_flow_entities
    import octobot_flow.enums as octobot_flow_enums
    import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
    import octobot_trading.constants as trading_constants_module
    import octobot_trading.enums as trading_enums_module
    import octobot_trading.exchanges.util.exchange_data as exchange_data_module
    import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools_module
    import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading_module

    import octobot_node.scheduler.workflows.params as workflow_params_module
    import octobot_node.scheduler.workflows_util as workflows_util_module

    IMPORTED_OCTOBOT_FLOW_GRID_DEPS = True
except ImportError:
    dsl_interpreter_module = None  # type: ignore
    octobot_flow_entities = None  # type: ignore
    octobot_flow_enums = None  # type: ignore
    octobot_flow_repositories_exchange_module = None  # type: ignore
    workflow_params_module = None  # type: ignore
    workflows_util_module = None  # type: ignore


_AUTOMATION_ID = "automation_1"

_T_ENQUEUE_SECONDS = 5.0
_T_GRID_SECONDS = 20.0
_T_STOP_SEND_SECONDS = 5.0
_T_STOP_COMPLETE_SECONDS = 10.0
_POLL_INTERVAL_SECONDS = 0.5

_GRID_INCREMENT = 200
_GRID_SPREAD = 600
_FIXED_BTC_USDC_CLOSE = 100000.0

# Wallet for this flow: set on ``Task.wallet_address``; ``OctoBotActionsJob`` merges it into auth_details (not from task JSON).
_SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS = "simulator-copy-grid-functional-test-wallet-address"


def _is_on_github_ci() -> bool:
    return bool(os.getenv("GITHUB_ACTIONS"))


def _exchange_internal_name() -> str:
    return "binanceus" if _is_on_github_ci() else "binance"


if IMPORTED_OCTOBOT_FLOW_GRID_DEPS:
    _grid_pair_settings = [
        grid_trading_module.GridTradingMode.get_default_pair_config(
            "BTC/USDC",
            _GRID_SPREAD,
            _GRID_INCREMENT,
            2,
            2,
            False,
            False,
            False,
        )
    ]

    def _grid_trading_mode_action_dict(dependency_action: dict[str, typing.Any]) -> dict[str, typing.Any]:
        return {
            "id": "action_1",
            "dsl_script": (
                f"grid_trading_mode(pair_settings={dsl_interpreter_module.format_parameter_value(_grid_pair_settings)})"
            ),
            "dependencies": [{"action_id": dependency_action["id"]}],
        }

    def _simulator_grid_init_action_dict() -> dict[str, typing.Any]:
        return {
            "id": "action_init",
            "action": octobot_flow_enums.ActionType.APPLY_CONFIGURATION.value,
            "config": {
                "automation": {
                    "metadata": {
                        "automation_id": _AUTOMATION_ID,
                    },
                    "exchange_account_elements": {
                        "portfolio": {
                            "content": {
                                "USDC": {
                                    "available": 1000.0,
                                    "total": 1000.0,
                                }
                            },
                        },
                    },
                },
                "exchange_account_details": {
                    "exchange_details": {
                        "internal_name": _exchange_internal_name(),
                    },
                    "auth_details": {},
                    "portfolio": {
                        "unit": "USDC",
                    },
                },
            },
        }

    def _fetch_ohlcv_side_effect_for_close_price(
        get_close_price: typing.Callable[[], typing.Union[int, float]],
    ):
        async def patched_fetch_ohlcv(
            symbol: str,
            time_frame: str,
            limit: int,
            _tickers: dict[str, dict[str, typing.Any]],
        ):
            # Step: build deterministic OHLCV rows pinned to ``get_close_price`` (mirrors grid functional test).
            time_frame_seconds = common_enums_module.TimeFramesMinutes[common_enums_module.TimeFrames(time_frame)] * 60
            close_price = float(get_close_price())
            candle_count = max(int(limit or 1), 1)
            local_time = time.time()
            current_candle_open_time = local_time - (local_time % time_frame_seconds)
            first_candle_open_time = current_candle_open_time - (candle_count - 1) * time_frame_seconds
            times = [
                float(first_candle_open_time + step_index * time_frame_seconds)
                for step_index in range(candle_count)
            ]
            closes = [close_price] * candle_count
            ohlc = [close_price] * candle_count
            return exchange_data_module.MarketDetails(
                symbol=symbol,
                time_frame=time_frame,
                close=closes,
                open=ohlc,
                high=ohlc,
                low=ohlc,
                volume=[0.0] * candle_count,
                time=times,
            )

        return patched_fetch_ohlcv

    def _tickers_repository_fetch_tickers_btc_usdc_close_override(
        get_btc_usdc_close: typing.Callable[[], typing.Union[int, float]],
        *,
        btc_usdc_symbol: str = "BTC/USDC",
    ):
        orig_get_all = exchanges_test_tools_module.get_all_currencies_price_ticker
        orig_get_one = exchanges_test_tools_module.get_price_ticker
        close_col = trading_enums_module.ExchangeConstantsTickersColumns.CLOSE.value

        async def patched_get_all_currencies_price_ticker(exchange_manager, **kwargs):
            tickers = await orig_get_all(exchange_manager, **kwargs)
            close_value = get_btc_usdc_close()
            if btc_usdc_symbol in tickers:
                tickers[btc_usdc_symbol] = {**tickers[btc_usdc_symbol], close_col: close_value}
            else:
                tickers[btc_usdc_symbol] = {close_col: close_value}
            return tickers

        async def patched_get_price_ticker(exchange_manager, symbol: str, **kwargs):
            if symbol == btc_usdc_symbol:
                return {close_col: get_btc_usdc_close()}
            return await orig_get_one(exchange_manager, symbol, **kwargs)

        async def patched_fetch_tickers(self, symbols):
            if symbols == []:
                return {}
            if isinstance(symbols, list) and len(symbols) == 1:
                return {
                    symbols[0]: await patched_get_price_ticker(self.exchange_manager, symbols[0])
                }
            return await patched_get_all_currencies_price_ticker(self.exchange_manager, symbols=None)

        return patched_fetch_tickers

    def _parse_automation_workflow_output(
        workflow_output: str,
    ) -> workflow_params_module.AutomationWorkflowOutput:
        payload = json.loads(workflow_output)
        return workflow_params_module.AutomationWorkflowOutput.from_dict(payload)

    def _job_description_dict_from_output(
        parsed: workflow_params_module.AutomationWorkflowOutput,
    ) -> dict[str, typing.Any]:
        assert isinstance(parsed.state, str)
        return json.loads(parsed.state)

    def _buy_sell_trade_counts_from_exchange_elements(
        exchange_account_elements: typing.Any,
    ) -> tuple[int, int, int]:
        if exchange_account_elements is None:
            return 0, 0, 0
        orders_container = getattr(exchange_account_elements, "orders", None)
        if orders_container is None and isinstance(exchange_account_elements, dict):
            orders_container = exchange_account_elements.get("orders")
        if orders_container is None:
            trades_only = getattr(exchange_account_elements, "trades", None)
            if trades_only is None and isinstance(exchange_account_elements, dict):
                trades_only = exchange_account_elements.get("trades", [])
            return 0, 0, len(trades_only or [])

        open_orders = getattr(orders_container, "open_orders", None)
        if open_orders is None and isinstance(orders_container, dict):
            open_orders = orders_container.get("open_orders", [])
        open_orders = open_orders or []

        side_key = trading_enums_module.ExchangeConstantsOrderColumns.SIDE.value
        storage_key = trading_constants_module.STORAGE_ORIGIN_VALUE
        buy_count = 0
        sell_count = 0
        for order in open_orders:
            if isinstance(order, dict):
                origin = order.get(storage_key, {})
            else:
                origin = getattr(order, storage_key, {})
            side = origin.get(side_key) if isinstance(origin, dict) else getattr(origin, side_key, None)
            if side == trading_enums_module.TradeOrderSide.BUY.value:
                buy_count += 1
            elif side == trading_enums_module.TradeOrderSide.SELL.value:
                sell_count += 1

        trades = getattr(exchange_account_elements, "trades", None)
        if trades is None and isinstance(exchange_account_elements, dict):
            trades = exchange_account_elements.get("trades", [])
        trade_count = len(trades or [])
        return buy_count, sell_count, trade_count

    def _grid_ready(buy_count: int, sell_count: int, trade_count: int) -> bool:
        return buy_count == 2 and sell_count == 2 and trade_count == 1

    def _build_grid_automation_state_dict() -> dict[str, typing.Any]:
        init_action = _simulator_grid_init_action_dict()
        all_actions = [init_action, _grid_trading_mode_action_dict(init_action)]
        state_payload: dict[str, typing.Any] = {
            "automation": {
                "metadata": {"automation_id": _AUTOMATION_ID},
                "actions_dag": {"actions": all_actions},
            }
        }
        return state_payload


@pytest.mark.skipif(not IMPORTED_OCTOBOT_FLOW_GRID_DEPS, reason="octobot_flow / grid tentacle deps not available")
class TestTriggerTaskGridDbosIntegration:
    @pytest.mark.asyncio
    async def test_trigger_task_grid_simulator_two_iterations_then_stop(self, temp_dbos_scheduler):
        patched_fetch_tickers = _tickers_repository_fetch_tickers_btc_usdc_close_override(
            lambda: _FIXED_BTC_USDC_CLOSE
        )
        patched_fetch_ohlcv = _fetch_ohlcv_side_effect_for_close_price(lambda: _FIXED_BTC_USDC_CLOSE)

        state_payload = _build_grid_automation_state_dict()
        task_content = json.dumps({"state": state_payload})
        grid_task = octobot_node.models.Task(
            name="test_grid_trigger_automation",
            content=task_content,
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
            wallet_address=_SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
        )

        # The only mocks are symbol prices to avoid side effects; everything else runs on the target environment.
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
        ):
            try:
                await asyncio.wait_for(
                    octobot_node.scheduler.tasks.trigger_task(grid_task),
                    timeout=_T_ENQUEUE_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("trigger_task timed out enqueueing automation workflow") from exc

            # Step 1: wait until simulator grid populated the ladder (2 buys, 2 sells) and optimisation trade exists.
            grid_deadline = time.monotonic() + _T_GRID_SECONDS
            automation_reader_matching: typing.Any = None
            while time.monotonic() < grid_deadline:
                workflow_rows = await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                grid_predicate_met = False
                for workflow_row in workflow_rows:
                    if workflows_util_module.get_automation_id(workflow_row) != _AUTOMATION_ID:
                        continue
                    state_reader = workflows_util_module.get_automation_state_reader(workflow_row)
                    if state_reader is None:
                        continue
                    elements = state_reader.state.automation.exchange_account_elements
                    buy_orders, sell_orders, trade_bucket = (
                        _buy_sell_trade_counts_from_exchange_elements(elements)
                    )
                    automation_reader_matching = automation_reader_matching or state_reader
                    if _grid_ready(buy_orders, sell_orders, trade_bucket):
                        automation_reader_matching = state_reader
                        grid_predicate_met = True
                        break
                if grid_predicate_met:
                    break
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            else:
                if automation_reader_matching is None:
                    pytest.fail(
                        "Timed out before any readable automation workflow state existed for automation_1"
                    )
                last_buys, last_sells, last_trades = (
                    _buy_sell_trade_counts_from_exchange_elements(
                        automation_reader_matching.state.automation.exchange_account_elements
                    )
                )
                pytest.fail(
                    f"Timed out waiting for grid state (wanted 2 buy, 2 sell, 1 trade); "
                    f"last seen buys={last_buys}, sells={last_sells}, trades={last_trades}"
                )

            elems_after_grid = automation_reader_matching.state.automation.exchange_account_elements
            buys_grid, sells_grid, trades_grid = _buy_sell_trade_counts_from_exchange_elements(
                elems_after_grid
            )
            assert _grid_ready(buys_grid, sells_grid, trades_grid)

            stop_priority_action = {
                "id": "action_stop_priority",
                "dsl_script": "stop_automation()",
            }
            try:
                await asyncio.wait_for(
                    octobot_node.scheduler.tasks.send_actions_to_automation(
                        [stop_priority_action], _AUTOMATION_ID
                    ),
                    timeout=_T_STOP_SEND_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("send_actions_to_automation timed out") from exc

            # Step 2: wait for terminate output and confirm priority stop plus preserved orders/trades.
            stop_deadline = time.monotonic() + _T_STOP_COMPLETE_SECONDS
            final_output_text: typing.Optional[str] = None
            while time.monotonic() < stop_deadline:
                workflow_rows = await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                for workflow_row in workflow_rows:
                    if workflow_row.status != dbos.WorkflowStatusString.SUCCESS.value:
                        continue
                    if workflows_util_module.get_automation_id(workflow_row) != _AUTOMATION_ID:
                        continue
                    workflow_handle = await temp_dbos_scheduler.INSTANCE.retrieve_workflow_async(
                        workflow_row.workflow_id
                    )
                    result_text = await workflow_handle.get_result()
                    if not result_text:
                        continue
                    parsed_output = _parse_automation_workflow_output(result_text)
                    if parsed_output.error:
                        continue
                    job_dict = _job_description_dict_from_output(parsed_output)
                    automation_payload = job_dict["state"]["automation"]
                    if automation_payload.get("post_actions", {}).get("stop_automation"):
                        final_output_text = result_text
                        break
                if final_output_text is not None:
                    break
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            else:
                pytest.fail(
                    "Timed out waiting for workflow stop completion and final AutomationWorkflowOutput"
                )

            assert final_output_text is not None
            parsed_final = _parse_automation_workflow_output(final_output_text)
            assert parsed_final.error is None
            final_job = _job_description_dict_from_output(parsed_final)
            # OctoBotActionsJobDescription: only non-default fields are serialized (empty params omitted).
            # _SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS has been added to auth_details
            assert set(final_job.keys()) == {"auth_details", "state"}
            final_auth_details = octobot_flow_entities.UserAuthentication.from_dict(
                final_job["auth_details"]
            )
            assert final_auth_details.wallet_address == _SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS
            final_automation = final_job["state"]["automation"]
            assert final_automation["post_actions"]["stop_automation"] is True
            final_elements = final_automation["exchange_account_elements"]
            final_buys, final_sells, final_trades = _buy_sell_trade_counts_from_exchange_elements(
                final_elements
            )
            assert _grid_ready(final_buys, final_sells, final_trades)
