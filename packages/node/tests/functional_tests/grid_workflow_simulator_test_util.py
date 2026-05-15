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
import datetime
import json
import math
import time
import typing
import uuid

import dbos
import pytest

IMPORTED_OCTOBOT_FLOW_GRID_DEPS = False
try:
    import octobot_commons.enums as common_enums_module
    import octobot_trading.constants as trading_constants_module
    import octobot_trading.enums as trading_enums_module
    import octobot_trading.exchanges.util.exchange_data as exchange_data_module
    import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools_module

    import octobot_node.constants as node_constants_module
    import octobot_node.scheduler.api as scheduler_api_module
    import octobot_node.scheduler.workflows.params as workflow_params_module
    import octobot_node.scheduler.workflows_util as workflows_util_module
    import octobot_protocol.models as protocol_models_module

    IMPORTED_OCTOBOT_FLOW_GRID_DEPS = True
except ImportError:
    common_enums_module = None  # type: ignore
    trading_constants_module = None  # type: ignore
    trading_enums_module = None  # type: ignore
    exchange_data_module = None  # type: ignore
    exchanges_test_tools_module = None  # type: ignore
    workflow_params_module = None  # type: ignore
    workflows_util_module = None  # type: ignore
    node_constants_module = None  # type: ignore
    scheduler_api_module = None  # type: ignore
    protocol_models_module = None  # type: ignore


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

_FUNCTIONAL_PROTOCOL_ACCOUNT_TS = datetime.datetime(2026, 4, 1, 12, 0, 0, tzinfo=datetime.UTC)

def exchange_internal_name() -> str:
    # Match CI so local runs exercise the same precision/fees as GitHub Actions.
    return "binanceus"


if IMPORTED_OCTOBOT_FLOW_GRID_DEPS:
    def _wrap_user_action_configuration(payload) -> protocol_models_module.UserActionConfiguration:
        return protocol_models_module.UserActionConfiguration.from_json(payload.to_json())

    def protocol_exchange_account_for_grid_functional(*, usdc_total: float) -> protocol_models_module.ExchangeAccount:
        return protocol_models_module.ExchangeAccount(
            account_type=protocol_models_module.AccountType.EXCHANGE,
            trading_type=protocol_models_module.TradingType.SPOT,
            exchange=exchange_internal_name(),
            remote_account_id="functional-test-account",
            api_key="functional-key",
            api_secret="functional-secret",
            assets=[
                protocol_models_module.Asset(
                    symbol="USDC",
                    total=usdc_total,
                    available=usdc_total,
                    unit="USDC",
                )
            ],
        )

    def protocol_account_for_functional(
        *,
        account_id: str,
        usdc_total: float,
        account_name: str = "Functional test account",
    ) -> protocol_models_module.Account:
        return protocol_models_module.Account(
            id=account_id,
            name=account_name,
            is_simulated=True,
            created_at=_FUNCTIONAL_PROTOCOL_ACCOUNT_TS,
            updated_at=_FUNCTIONAL_PROTOCOL_ACCOUNT_TS,
            details=protocol_models_module.AccountDetails(
                actual_instance=protocol_exchange_account_for_grid_functional(usdc_total=usdc_total),
            ),
        )

    SIMULATOR_GRID_DEFAULT_STRATEGY_ID = "simulator-grid-functional-default-strategy"
    SIMULATOR_FUNCTIONAL_STRATEGY_VERSION = "1.0.0"
    SIMULATOR_COPY_FOLLOWER_STORED_STRATEGY_ID = "simulator-functional-copy-stored-strategy"

    def seeded_grid_strategy_for_functional_wallet(
        *,
        stored_strategy_id: str,
    ) -> protocol_models_module.Strategy:
        """
        Persisted Strategy row keyed by ``stored_strategy_id`` (matches ``StrategyReference.id`` on the user action).
        """
        return protocol_models_module.Strategy(
            id=stored_strategy_id,
            version=SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
            name="Simulator grid automation strategy",
            configuration=protocol_models_module.StrategyConfiguration(
                grid_configuration_matching_simulator_constants(),
            ),
        )

    def seeded_copy_follower_strategy_for_functional_wallet(
        *,
        copy_master_strategy_id: str,
    ) -> protocol_models_module.Strategy:
        """
        Copy follower strategy document: ``StrategyReference.id`` matches
        ``SIMULATOR_COPY_FOLLOWER_STORED_STRATEGY_ID``; ``CopyConfiguration.strategy_id``
        selects the master's signal strategy id on the broker.
        """
        return protocol_models_module.Strategy(
            id=SIMULATOR_COPY_FOLLOWER_STORED_STRATEGY_ID,
            version=SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
            name="Simulator copy-follower automation strategy",
            configuration=protocol_models_module.StrategyConfiguration(
                protocol_models_module.CopyConfiguration(
                    configuration_type=protocol_models_module.ActionConfigurationType.COPY,
                    strategy_id=copy_master_strategy_id,
                )
            ),
        )

    def grid_configuration_matching_simulator_constants() -> protocol_models_module.GridConfiguration:
        return protocol_models_module.GridConfiguration(
            configuration_type=protocol_models_module.ActionConfigurationType.GRID,
            symbol="BTC/USDC",
            spread=GRID_SPREAD,
            increment=GRID_INCREMENT,
            buy_count=2,
            sell_count=2,
            enable_trailing_up=False,
            enable_trailing_down=False,
            order_by_order_trailing=False,
        )

    def build_create_grid_user_action(
        *,
        account_id: str,
        name: str,
        strategy_id: str | None = None,
        emit_signals: bool | None = None,
    ) -> protocol_models_module.UserAction:
        reference_strategy_identifier = strategy_id or SIMULATOR_GRID_DEFAULT_STRATEGY_ID
        strategy_reference = protocol_models_module.StrategyReference(
            id=reference_strategy_identifier,
            version=SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
            emit_signals=emit_signals if emit_signals is not None else False,
        )
        automation_configuration = protocol_models_module.AutomationConfiguration(
            name=name,
            created_at=datetime.datetime(2026, 5, 10, 8, 0, 0, tzinfo=datetime.UTC),
            strategy=strategy_reference,
            accounts=[protocol_models_module.AccountReference(id=account_id)],
        )
        payload = protocol_models_module.CreateAutomationConfiguration(
            action_type=protocol_models_module.UserActionType.AUTOMATION_CREATE,
            configuration=automation_configuration,
        )
        return protocol_models_module.UserAction(
            id=f"ua-grid-{uuid.uuid4()}",
            configuration=_wrap_user_action_configuration(payload),
        )

    def build_create_copy_follower_user_action(
        *,
        automation_id: str,
        account_id: str,
        name: str,
        strategy_id: str,
    ) -> protocol_models_module.UserAction:
        strategy_reference = protocol_models_module.StrategyReference(
            id=SIMULATOR_COPY_FOLLOWER_STORED_STRATEGY_ID,
            version=SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
        )
        automation_configuration = protocol_models_module.AutomationConfiguration(
            name=name,
            created_at=datetime.datetime(2026, 5, 10, 8, 1, 0, tzinfo=datetime.UTC),
            strategy=strategy_reference,
            accounts=[protocol_models_module.AccountReference(id=account_id)],
        )
        payload = protocol_models_module.CreateAutomationConfiguration(
            action_type=protocol_models_module.UserActionType.AUTOMATION_CREATE,
            configuration=automation_configuration,
        )
        return protocol_models_module.UserAction(
            id=automation_id,
            configuration=_wrap_user_action_configuration(payload),
        )

    def build_stop_user_action(
        *,
        automation_id: str,
        user_action_id: str,
    ) -> protocol_models_module.UserAction:
        payload = protocol_models_module.StopAutomationConfiguration(
            action_type=protocol_models_module.UserActionType.AUTOMATION_STOP,
            id=automation_id,
        )
        return protocol_models_module.UserAction(
            id=user_action_id,
            configuration=_wrap_user_action_configuration(payload),
        )

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

    def find_protocol_automation_state(
        automation_states: list[protocol_models_module.AutomationState],
        parent_workflow_id: str,
    ) -> typing.Optional[protocol_models_module.AutomationState]:
        normalized_id = parent_workflow_id[: node_constants_module.PARENT_WORKFLOW_ID_LENGTH]
        for automation in automation_states:
            if automation.id == normalized_id:
                return automation
        return None

    async def load_protocol_automation_state_for_workflow(
        wallet_address: typing.Optional[str],
        workflow_row: dbos.WorkflowStatus,
    ) -> protocol_models_module.AutomationState:
        parent_id = workflow_row.workflow_id[: node_constants_module.PARENT_WORKFLOW_ID_LENGTH]
        automation_states = await scheduler_api_module.get_automation_states(wallet_address)
        automation_state = find_protocol_automation_state(automation_states, parent_id)
        if automation_state is None:
            seen_ids = [automation.id for automation in automation_states]
            raise AssertionError(
                f"No AutomationState entry for parent_workflow_id={parent_id!r}; "
                f"returned automation ids: {seen_ids!r}"
            )
        return automation_state

    def _portfolio_content_from_exchange_elements(exchange_account_elements: typing.Any) -> dict[str, typing.Any]:
        portfolio = getattr(exchange_account_elements, "portfolio", None)
        if portfolio is None and isinstance(exchange_account_elements, dict):
            portfolio = exchange_account_elements.get("portfolio")
        if portfolio is None:
            return {}
        content = getattr(portfolio, "content", None)
        if content is None and isinstance(portfolio, dict):
            content = portfolio.get("content")
        return content if isinstance(content, dict) else {}

    def _portfolio_row_scalar(row: typing.Any, field_name: str) -> float:
        if isinstance(row, dict):
            raw_value = row.get(field_name)
        else:
            raw_value = getattr(row, field_name, None)
        if raw_value is None and field_name == "available":
            return _portfolio_row_scalar(row, "total")
        if raw_value is None:
            raise AssertionError(f"portfolio row missing field {field_name!r}: {row!r}")
        return float(raw_value)

    def assert_protocol_automation_matches_exchange_account_elements(
        protocol_automation: protocol_models_module.AutomationState,
        exchange_account_elements: typing.Any,
        *,
        expected_automation_task_status: protocol_models_module.TaskStatus,
        expected_order_symbol: str = "BTC/USDC",
    ) -> None:
        assert protocol_automation.status == expected_automation_task_status, (
            f"AutomationState.status is {protocol_automation.status.value!r}; "
            f"expected {expected_automation_task_status.value!r}"
        )
        buy_orders, sell_orders, flow_trade_count = buy_sell_trade_counts_from_exchange_elements(
            exchange_account_elements,
        )
        expected_open_count = buy_orders + sell_orders
        protocol_orders = protocol_automation.orders or []
        protocol_trades = protocol_automation.trades or []
        assert len(protocol_orders) == expected_open_count, (
            f"protocol open order count {len(protocol_orders)} != flow open orders {expected_open_count} "
            f"(buy={buy_orders}, sell={sell_orders})"
        )
        assert len(protocol_trades) == flow_trade_count, (
            f"protocol trade count {len(protocol_trades)} != flow trade count {flow_trade_count}"
        )
        for order_summary in protocol_orders:
            assert order_summary.symbol == expected_order_symbol, (
                f"unexpected OrderSummary.symbol {order_summary.symbol!r}; expected {expected_order_symbol!r}"
            )
        content = _portfolio_content_from_exchange_elements(exchange_account_elements)
        assets = protocol_automation.assets or []
        assets_by_symbol = {asset.symbol: asset for asset in assets}
        for symbol, row in content.items():
            matching_asset = assets_by_symbol.get(symbol)
            assert matching_asset is not None, (
                f"missing protocol Asset for portfolio symbol {symbol!r}; "
                f"protocol asset symbols: {sorted(assets_by_symbol)!r}"
            )
            expected_total = _portfolio_row_scalar(row, "total")
            expected_available = _portfolio_row_scalar(row, "available")
            if not math.isclose(float(matching_asset.total), expected_total, rel_tol=1e-9, abs_tol=1e-6):
                raise AssertionError(
                    f"Asset.total mismatch for {symbol!r}: protocol={matching_asset.total!r} "
                    f"flow={expected_total!r}"
                )
            if not math.isclose(float(matching_asset.available), expected_available, rel_tol=1e-9, abs_tol=1e-6):
                raise AssertionError(
                    f"Asset.available mismatch for {symbol!r}: protocol={matching_asset.available!r} "
                    f"flow={expected_available!r}"
                )

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


async def enqueue_user_action_workflow_and_await_terminal_result(
    scheduler: typing.Any,
    user_action_bundle: typing.Any,
    wallet_address_segment: str,
):
    """``execute_user_action`` queues user actions; wait until the USER_ACTION_QUEUE workflow completes."""
    import octobot_node.scheduler.tasks as scheduler_tasks_module

    workflow_identifier_encoded = await scheduler_tasks_module.trigger_user_action_workflow(
        user_action_bundle,
        wallet_address_segment,
    )
    terminal_handle_encoded = await scheduler.INSTANCE.retrieve_workflow_async(workflow_identifier_encoded)
    await terminal_handle_encoded.get_result()
