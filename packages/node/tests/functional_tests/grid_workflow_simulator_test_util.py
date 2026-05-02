#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at your
#  option) any later version.
#
#  OctoBot Node is distributed in the hope that it will be useful, but WITHOUT ANY
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  OctoBot Node. If not, see https://www.gnu.org/licenses/.
"""Helpers shared by grid simulator automation DBOS functional tests."""

from __future__ import annotations

import asyncio
import json
import time
import typing

import dbos
import pytest

IMPORTED_OCTOBOT_FLOW_GRID_DEPS = False
try:
    import octobot_commons.dsl_interpreter as dsl_interpreter_module
    import octobot_commons.enums as common_enums_module
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
    common_enums_module = None  # type: ignore
    octobot_flow_enums = None  # type: ignore
    octobot_flow_repositories_exchange_module = None  # type: ignore
    trading_constants_module = None  # type: ignore
    trading_enums_module = None  # type: ignore
    exchange_data_module = None  # type: ignore
    exchanges_test_tools_module = None  # type: ignore
    grid_trading_module = None  # type: ignore
    workflow_params_module = None  # type: ignore
    workflows_util_module = None  # type: ignore


# Passphrase for grid functional tests (WalletBackend requires length >= 8).
SIMULATOR_GRID_TEST_WALLET_PASSPHRASE = "simgridPW1!"

if IMPORTED_OCTOBOT_FLOW_GRID_DEPS:
    import octobot_sync.chain.evm as sync_evm_module

    # Hardhat/Anvil-style dev key #0 — deterministic address for CI and local wallet import.
    SIMULATOR_GRID_TEST_PRIVATE_KEY = (
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS = sync_evm_module.address_from_evm_key(
        SIMULATOR_GRID_TEST_PRIVATE_KEY
    ).lower()
else:
    sync_evm_module = None  # type: ignore
    SIMULATOR_GRID_TEST_PRIVATE_KEY = ""
    SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS = "simulator-copy-grid-functional-test-wallet-address"

GRID_INCREMENT = 200
GRID_SPREAD = 600
FIXED_BTC_USDC_CLOSE = 100000.0

DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS = 0.5


def exchange_internal_name() -> str:
    # Match CI so local runs exercise the same precision/fees as GitHub Actions.
    return "binanceus"


if IMPORTED_OCTOBOT_FLOW_GRID_DEPS:
    GRID_PAIR_SETTINGS = [
        grid_trading_module.GridTradingMode.get_default_pair_config(
            "BTC/USDC",
            GRID_SPREAD,
            GRID_INCREMENT,
            2,
            2,
            False,
            False,
            False,
        )
    ]

    def grid_trading_mode_action_dict(dependency_action: dict[str, typing.Any]) -> dict[str, typing.Any]:
        return {
            "id": "action_1",
            "dsl_script": (
                f"grid_trading_mode(pair_settings={dsl_interpreter_module.format_parameter_value(GRID_PAIR_SETTINGS)})"
            ),
            "dependencies": [{"action_id": dependency_action["id"]}],
        }

    def simulator_grid_init_action_dict(automation_id: str, usdc_total: float) -> dict[str, typing.Any]:
        return {
            "id": "action_init",
            "action": octobot_flow_enums.ActionType.APPLY_CONFIGURATION.value,
            "config": {
                "automation": {
                    "metadata": {
                        "automation_id": automation_id,
                    },
                    "exchange_account_elements": {
                        "portfolio": {
                            "content": {
                                "USDC": {
                                    "available": usdc_total,
                                    "total": usdc_total,
                                }
                            },
                        },
                    },
                },
                "exchange_account_details": {
                    "exchange_details": {
                        "internal_name": exchange_internal_name(),
                    },
                    "auth_details": {},
                    "portfolio": {
                        "unit": "USDC",
                    },
                },
            },
        }

    def build_simple_grid_simulator_state_dict(automation_id: str, usdc_initial: float) -> dict[str, typing.Any]:
        init_action = simulator_grid_init_action_dict(automation_id, usdc_initial)
        all_actions = [init_action, grid_trading_mode_action_dict(init_action)]
        return {
            "automation": {
                "metadata": {"automation_id": automation_id},
                "actions_dag": {"actions": all_actions},
            }
        }

    def fetch_ohlcv_side_effect_for_close_price(
        get_close_price: typing.Callable[[], typing.Union[int, float]],
    ):
        async def patched_fetch_ohlcv(
            symbol: str,
            time_frame: str,
            limit: int,
            _tickers: dict[str, dict[str, typing.Any]],
        ):
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

    def tickers_repository_fetch_tickers_btc_usdc_close_override(
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

    def parse_automation_workflow_output(
        workflow_output: str,
    ) -> workflow_params_module.AutomationWorkflowOutput:
        payload = json.loads(workflow_output)
        return workflow_params_module.AutomationWorkflowOutput.from_dict(payload)

    def job_description_dict_from_output(
        parsed: workflow_params_module.AutomationWorkflowOutput,
    ) -> dict[str, typing.Any]:
        assert isinstance(parsed.state, str)
        return json.loads(parsed.state)

    def buy_sell_trade_counts_from_exchange_elements(
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
                inner = order.get(storage_key, {})
            else:
                inner = getattr(order, storage_key, {})
            side = inner.get(side_key) if isinstance(inner, dict) else getattr(inner, side_key, None)
            if side == trading_enums_module.TradeOrderSide.BUY.value:
                buy_count += 1
            elif side == trading_enums_module.TradeOrderSide.SELL.value:
                sell_count += 1

        trades = getattr(exchange_account_elements, "trades", None)
        if trades is None and isinstance(exchange_account_elements, dict):
            trades = exchange_account_elements.get("trades", [])
        trade_count = len(trades or [])
        return buy_count, sell_count, trade_count

    def is_simulator_grid_baseline_exactly_one_trade(buy_count: int, sell_count: int, trade_count: int) -> bool:
        return buy_count == 2 and sell_count == 2 and trade_count == 1

    def is_simulator_grid_baseline_at_least_one_trade(buy_count: int, sell_count: int, trade_count: int) -> bool:
        return buy_count == 2 and sell_count == 2 and trade_count >= 1

    async def wait_for_stop_success_output(
        scheduler,
        automation_id: str,
        deadline_seconds: float,
        *,
        poll_interval_seconds: float = DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS,
    ) -> str:
        stop_deadline = time.monotonic() + deadline_seconds
        while time.monotonic() < stop_deadline:
            workflow_rows = await scheduler.INSTANCE.list_workflows_async()
            for workflow_row in workflow_rows:
                if workflow_row.status != dbos.WorkflowStatusString.SUCCESS.value:
                    continue
                if workflows_util_module.get_automation_id(workflow_row) != automation_id:
                    continue
                workflow_handle = await scheduler.INSTANCE.retrieve_workflow_async(workflow_row.workflow_id)
                result_text = await workflow_handle.get_result()
                if not result_text:
                    continue
                parsed_output = parse_automation_workflow_output(result_text)
                if parsed_output.error:
                    continue
                job_dict = job_description_dict_from_output(parsed_output)
                automation_payload = job_dict["state"]["automation"]
                if automation_payload.get("post_actions", {}).get("stop_automation"):
                    return result_text
            await asyncio.sleep(poll_interval_seconds)
        pytest.fail(f"Timed out waiting for stop completion for {automation_id}")
