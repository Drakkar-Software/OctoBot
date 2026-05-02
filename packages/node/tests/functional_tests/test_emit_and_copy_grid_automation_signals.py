#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at your
#  option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful, but WITHOUT ANY
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  OctoBot. If not, see https://www.gnu.org/licenses/.
from __future__ import annotations

import asyncio
import contextlib
import copy as copy_stdlib
import decimal
import json
import logging
import mock
import time
import typing

import pytest

import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel_module
import octobot_node.models
import octobot_node.scheduler.internal_trading_signals as internal_trading_signals_module
import octobot_node.scheduler.tasks

from . import grid_workflow_simulator_test_util as grid_sim_util
from tests.scheduler import temp_dbos_scheduler


IMPORTED_OCTOBOT_FLOW_GRID_DEPS = False
if grid_sim_util.IMPORTED_OCTOBOT_FLOW_GRID_DEPS:
    try:
        import octobot_commons.constants as octobot_commons_constants_module
        import octobot_copy.constants as octobot_copy_constants_module
        import octobot_flow
        import octobot_flow.entities as octobot_flow_entities
        import octobot_flow.repositories.community as octobot_flow_repositories_community_module
        import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
        import octobot_trading.enums as trading_enums_module
        IMPORTED_OCTOBOT_FLOW_GRID_DEPS = True
    except ImportError:
        octobot_flow = None  # type: ignore
        octobot_commons_constants_module = None  # type: ignore
        octobot_copy_constants_module = None  # type: ignore
        octobot_flow_entities = None  # type: ignore
        octobot_flow_repositories_exchange_module = None  # type: ignore
        octobot_flow_repositories_community_module = None  # type: ignore


_MASTER_AUTOMATION_ID = "master_emit_grid"
_COPY_AUTOMATION_ID = "copy_grid_follower"
_SHARED_STRATEGY_ID = "functional_test_copy_strategy"

_MASTER_INIT_USDC = 10000.0
_COPY_INIT_USDC = 2000.0

_T_ENQUEUE_SECONDS = 5.0
_T_GRID_SECONDS = 25.0
_T_BOOTSTRAP_COPY_SECONDS = 25.0
_T_POST_SHOCK_SECONDS = 35.0
_T_STOP_SEND_SECONDS = 5.0
_T_STOP_COMPLETE_SECONDS = 15.0

_D_DECIMAL_INCREMENT = decimal.Decimal(str(grid_sim_util.GRID_INCREMENT))


if IMPORTED_OCTOBOT_FLOW_GRID_DEPS:

    @contextlib.asynccontextmanager
    async def _fake_maybe_authenticator(self):  # type: ignore[no-untyped-def]
        yield mock.MagicMock()

    def _empty_copy_exchange_account_action_dict() -> dict[str, typing.Any]:
        return {
            "id": "action_copy_exchange_account",
            "dsl_script": (
                f"copy_exchange_account(strategy_id={json.dumps(_SHARED_STRATEGY_ID)}, "
                "reference_market='', reference_account='')"
            ),
        }

    def _build_master_grid_state_dict() -> dict[str, typing.Any]:
        init_action = grid_sim_util.simulator_grid_init_action_dict(_MASTER_AUTOMATION_ID, _MASTER_INIT_USDC)
        all_actions = [init_action, grid_sim_util.grid_trading_mode_action_dict(init_action)]
        return {
            "automation": {
                "metadata": {
                    "automation_id": _MASTER_AUTOMATION_ID,
                    "emit_signals": True,
                    "strategy_id": _SHARED_STRATEGY_ID,
                },
                "actions_dag": {"actions": all_actions},
            }
        }

    def _build_copy_state_dict() -> dict[str, typing.Any]:
        init_action = grid_sim_util.simulator_grid_init_action_dict(_COPY_AUTOMATION_ID, _COPY_INIT_USDC)
        all_actions = [init_action, _empty_copy_exchange_account_action_dict()]
        return {
            "automation": {
                "metadata": {
                    "automation_id": _COPY_AUTOMATION_ID,
                },
                "actions_dag": {"actions": all_actions},
            }
        }

    def _post_fill_open_order_shape(buy_count: int, sell_count: int) -> bool:
        """Three open buys + one sell after smallest sell fills and grid mirrors."""
        return buy_count == 3 and sell_count == 1

    def _d_order_price(raw: typing.Union[int, float, str, decimal.Decimal]) -> decimal.Decimal:
        if isinstance(raw, decimal.Decimal):
            return raw
        return decimal.Decimal(str(raw))

    def _sorted_limit_prices_from_elements(
        exchange_account_elements: typing.Any,
        *,
        trade_order_side,
    ) -> list[decimal.Decimal]:
        if exchange_account_elements is None:
            return []
        orders_container = getattr(exchange_account_elements, "orders", None)
        if orders_container is None and isinstance(exchange_account_elements, dict):
            orders_container = exchange_account_elements.get("orders")
        if orders_container is None:
            return []
        open_orders = getattr(orders_container, "open_orders", None)
        if open_orders is None and isinstance(orders_container, dict):
            open_orders = orders_container.get("open_orders", [])
        open_orders = open_orders or []

        side_key = trading_enums_module.ExchangeConstantsOrderColumns.SIDE.value
        price_col = trading_enums_module.ExchangeConstantsOrderColumns.PRICE.value
        storage_key = grid_sim_util.trading_constants_module.STORAGE_ORIGIN_VALUE
        want_side = trade_order_side.value
        prices: list[decimal.Decimal] = []
        for order in open_orders:
            if isinstance(order, dict):
                inner = order.get(storage_key, {})
            else:
                inner = getattr(order, storage_key, {})
            side = inner.get(side_key) if isinstance(inner, dict) else getattr(inner, side_key, None)
            if side != want_side:
                continue
            price_raw = inner.get(price_col) if isinstance(inner, dict) else getattr(inner, price_col, None)
            if price_raw is None:
                continue
            type_col = trading_enums_module.ExchangeConstantsOrderColumns.TYPE.value
            if isinstance(inner, dict):
                order_type = inner.get(type_col)
            else:
                order_type = getattr(inner, type_col, None)
            if order_type is not None and order_type != trading_enums_module.TradeOrderType.LIMIT.value:
                continue
            prices.append(_d_order_price(price_raw))
        prices.sort()
        return prices

    def _assert_open_limit_prices_match_reference(
        reference_elements: typing.Any,
        follower_elements: typing.Any,
    ) -> None:
        for side in (
            trading_enums_module.TradeOrderSide.BUY,
            trading_enums_module.TradeOrderSide.SELL,
        ):
            ref_prices = _sorted_limit_prices_from_elements(reference_elements, trade_order_side=side)
            got_prices = _sorted_limit_prices_from_elements(follower_elements, trade_order_side=side)
            assert ref_prices == got_prices, f"side={side!r} ref={ref_prices!s} follower={got_prices!s}"

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

    def _portfolio_row_total(row: typing.Any) -> decimal.Decimal:
        total_key = octobot_commons_constants_module.PORTFOLIO_TOTAL
        if isinstance(row, dict):
            raw = row.get(total_key, row.get("total"))
        else:
            raw = getattr(row, total_key, None) or getattr(row, "total", None)
        if raw is None:
            raise AssertionError("portfolio row has no total amount")
        return raw if isinstance(raw, decimal.Decimal) else decimal.Decimal(str(raw))

    def _value_weighted_btc_usdc_shares(
        content: dict[str, typing.Any],
        *,
        btc_usdc_close: decimal.Decimal,
    ) -> dict[str, decimal.Decimal]:
        """USDC notionals: ``btc_total * btc_usdc_close`` vs USDC total; shares sum to 1."""
        for asset in ("BTC", "USDC"):
            assert asset in content, f"missing portfolio row for {asset}"
        btc_total = _portfolio_row_total(content["BTC"])
        usdc_total = _portfolio_row_total(content["USDC"])
        btc_notional_usdc = btc_total * btc_usdc_close
        usdc_notional = usdc_total
        total_notional = btc_notional_usdc + usdc_notional
        assert total_notional > 0, "expected positive portfolio value in USDC"
        return {
            "BTC": btc_notional_usdc / total_notional,
            "USDC": usdc_notional / total_notional,
        }

    def _assert_btc_usdc_value_shares_match_reference(
        reference_elements: typing.Any,
        follower_elements: typing.Any,
        *,
        btc_usdc_close: decimal.Decimal,
    ) -> None:
        ref_content = _portfolio_content_from_exchange_elements(reference_elements)
        follower_content = _portfolio_content_from_exchange_elements(follower_elements)
        ref_shares = _value_weighted_btc_usdc_shares(ref_content, btc_usdc_close=btc_usdc_close)
        follower_shares = _value_weighted_btc_usdc_shares(follower_content, btc_usdc_close=btc_usdc_close)
        # ~3 percentage points slack (master vs copy notionals / float portfolio totals).
        max_abs_diff = decimal.Decimal("0.03")
        for asset in ("BTC", "USDC"):
            delta = abs(ref_shares[asset] - follower_shares[asset])
            assert delta <= max_abs_diff, (
                f"{asset} value-share mismatch ref={ref_shares[asset]!s} "
                f"follower={follower_shares[asset]!s} (abs diff {delta!s}, max {max_abs_diff!s}) "
                f"at close={btc_usdc_close!s}"
            )

    def _first_sell_limit_price(exchange_account_elements: typing.Any) -> decimal.Decimal:
        sells = _sorted_limit_prices_from_elements(
            exchange_account_elements,
            trade_order_side=trading_enums_module.TradeOrderSide.SELL,
        )
        assert sells, "expected at least one open sell limit"
        return sells[0]

    async def _poll_state_reader_until(
        scheduler,
        automation_id: str,
        predicate: typing.Callable[[typing.Any], bool],
        deadline_seconds: float,
        failure_label: str,
    ) -> typing.Any:
        poll_interval = grid_sim_util.DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS
        poll_deadline = time.monotonic() + deadline_seconds
        last_reader: typing.Any = None
        while time.monotonic() < poll_deadline:
            workflow_rows = await scheduler.INSTANCE.list_workflows_async()
            for workflow_row in workflow_rows:
                if grid_sim_util.workflows_util_module.get_automation_id(workflow_row) != automation_id:
                    continue
                state_reader = grid_sim_util.workflows_util_module.get_automation_state_reader(workflow_row)
                if state_reader is None:
                    continue
                last_reader = state_reader
                if predicate(state_reader):
                    return state_reader
            await asyncio.sleep(poll_interval)
        detail = "no reader"
        if last_reader is not None:
            elements = last_reader.state.automation.exchange_account_elements
            detail = (
                f"last counts={grid_sim_util.buy_sell_trade_counts_from_exchange_elements(elements)}"
            )
        pytest.fail(f"Timed out waiting for {failure_label} ({detail})")

    _ORDERS_SYNCHRONIZER_LOGGER = "OrdersSynchronizer"
    _FORBIDDEN_ORDERS_SYNC_SUBSTRINGS = (
        "Cancelling mirrored order for replace",
        "Cancelled mirrored order for replace",
        "Mirrored orphan grace elapsed after",
        "Cancelled mirrored orphan order",
    )

    def _assert_orders_synchronizer_no_mirror_cancel_or_grace_logs(caplog) -> None:
        for record in caplog.records:
            if record.name != _ORDERS_SYNCHRONIZER_LOGGER:
                continue
            message_text = record.getMessage()
            for forbidden in _FORBIDDEN_ORDERS_SYNC_SUBSTRINGS:
                assert forbidden not in message_text, (
                    f"unexpected OrdersSynchronizer log ({forbidden!r}): {message_text!r}"
                )


@pytest.mark.skipif(not IMPORTED_OCTOBOT_FLOW_GRID_DEPS, reason="octobot_flow / grid tentacle deps not available")
class TestEmitAndCopyGridAutomationSignals:
    @pytest.mark.asyncio
    async def test_emit_and_copy_grid_master_forced_trigger_copies_signals(
        self, temp_dbos_scheduler, caplog
    ):
        """
        Master grid emits signals → copy bootstraps from mocked fetch_trading_signals → BTC price spikes,
        master's forced_trigger refills ladder and emits → internal trading signal channel notifies copy →
        copy mirrors master's open-limit prices; then both automations stop cleanly.
        """
        # Deterministic ticker/OHLCV close; bumped later past the lowest sell so that limit can fill.
        simulated_close: dict[str, float] = {"value": float(grid_sim_util.FIXED_BTC_USDC_CLOSE)}
        patched_fetch_tickers = grid_sim_util.tickers_repository_fetch_tickers_btc_usdc_close_override(
            lambda: simulated_close["value"]
        )
        patched_fetch_ohlcv = grid_sim_util.fetch_ohlcv_side_effect_for_close_price(
            lambda: simulated_close["value"]
        )

        captured_signals: list[octobot_flow_entities.TradingSignal] = []
        bootstrap_holder: dict[str, typing.Optional[octobot_flow_entities.TradingSignal]] = {"value": None}
        original_insert = octobot_flow_repositories_community_module.TradingSignalsRepository.insert_trading_signal

        # Preserve real insert logic (broadcast on internal channel) while recording payloads for bootstrap fetch wiring.
        async def _recording_insert_trading_signal(self, trading_signal: octobot_flow_entities.TradingSignal):
            captured_signals.append(trading_signal)
            return await original_insert(self, trading_signal)

        async def _fetch_side_effect(strategy_ids: list[str], history_size: int):
            # Until bootstrap is seeded, imitate an empty Starfish pull — copy waits for server signals only after freeze.
            if bootstrap_holder["value"] is None:
                return []
            return [copy_stdlib.deepcopy(bootstrap_holder["value"])]

        upload_trading_signal_mock = mock.AsyncMock()
        fetch_trading_signals_mock = mock.AsyncMock(side_effect=_fetch_side_effect)

        master_task = octobot_node.models.Task(
            name="test_master_emit_grid",
            content=json.dumps({"state": _build_master_grid_state_dict()}),
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
            wallet_address=grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
        )
        copy_task = octobot_node.models.Task(
            name="test_copy_grid_follower",
            content=json.dumps({"state": _build_copy_state_dict()}),
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
            wallet_address=grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
        )

        # Subscribe internal trading-signal consumer; tear down channel in ``finally``.
        await internal_trading_signals_module.subscribe_internal_trading_signal_consumer()
        try:
            # Prices patched; `_upload_trading_signal` skips server sync; inserts still hit internal channel (`send_*` untouched).
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
                mock.patch.object(
                    octobot_flow_repositories_community_module.TradingSignalsRepository,
                    "_upload_trading_signal",
                    upload_trading_signal_mock,
                ),
                mock.patch.object(
                    octobot_flow_repositories_community_module.TradingSignalsRepository,
                    "fetch_trading_signals",
                    fetch_trading_signals_mock,
                ),
                mock.patch.object(
                    octobot_flow_repositories_community_module.TradingSignalsRepository,
                    "insert_trading_signal",
                    _recording_insert_trading_signal,
                ),
                mock.patch.object(octobot_flow.AutomationJob, "_maybe_authenticator", _fake_maybe_authenticator),
            ):
                caplog.set_level(logging.INFO)
                try:
                    # Step 1 — enqueue master emitting grid signals; freeze last captured signal into fetch mock bootstrap.
                    await asyncio.wait_for(
                        octobot_node.scheduler.tasks.trigger_task(master_task),
                        timeout=_T_ENQUEUE_SECONDS,
                    )
                except TimeoutError as exc:
                    raise AssertionError("trigger_task timed out enqueueing master workflow") from exc

                master_reader = await _poll_state_reader_until(
                    temp_dbos_scheduler,
                    _MASTER_AUTOMATION_ID,
                    lambda reader: grid_sim_util.is_simulator_grid_baseline_at_least_one_trade(
                        *grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                            reader.state.automation.exchange_account_elements
                        )
                    ),
                    _T_GRID_SECONDS,
                    "master baseline grid (2 buy, 2 sell, >=1 trade)",
                )
                master_elements = master_reader.state.automation.exchange_account_elements
                buy_b, sell_b, trade_b = grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                    master_elements
                )
                assert grid_sim_util.is_simulator_grid_baseline_at_least_one_trade(buy_b, sell_b, trade_b)

                assert captured_signals, "expected master to emit at least one trading signal before copy starts"
                bootstrap_holder["value"] = copy_stdlib.deepcopy(captured_signals[-1])
                bootstrap_signal = bootstrap_holder["value"]
                assert bootstrap_signal.strategy_id == _SHARED_STRATEGY_ID
                bootstrap_account = bootstrap_signal.account
                assert bootstrap_account.content, "bootstrap signal should snapshot portfolio content"
                assert {"BTC", "USDC"} == set(bootstrap_account.content.keys())
                assert bootstrap_account.orders, "bootstrap signal should include open ladder orders"
                assert len(bootstrap_account.orders) == 4

                upload_trading_signal_mock.assert_awaited_with(bootstrap_signal)
                baseline_upload_count = upload_trading_signal_mock.await_count

                # Step 2 — enqueue copy fed by mocked fetch_trading_signals return value (mirroring server pull semantics).
                try:
                    await asyncio.wait_for(
                        octobot_node.scheduler.tasks.trigger_task(copy_task),
                        timeout=_T_ENQUEUE_SECONDS,
                    )
                except TimeoutError as exc:
                    raise AssertionError("trigger_task timed out enqueueing copy workflow") from exc

                copy_reader = await _poll_state_reader_until(
                    temp_dbos_scheduler,
                    _COPY_AUTOMATION_ID,
                    lambda reader: grid_sim_util.is_simulator_grid_baseline_at_least_one_trade(
                        *grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                            reader.state.automation.exchange_account_elements
                        )
                    ),
                    _T_BOOTSTRAP_COPY_SECONDS,
                    "copy baseline grid mirroring master",
                )
                _assert_open_limit_prices_match_reference(
                    master_reader.state.automation.exchange_account_elements,
                    copy_reader.state.automation.exchange_account_elements,
                )
                _assert_btc_usdc_value_shares_match_reference(
                    master_reader.state.automation.exchange_account_elements,
                    copy_reader.state.automation.exchange_account_elements,
                    btc_usdc_close=decimal.Decimal(str(simulated_close["value"])),
                )

                fetch_trading_signals_mock.assert_awaited_once_with(
                    [_SHARED_STRATEGY_ID],
                    octobot_copy_constants_module.DEFAULT_MISSED_SIGNALS_GRACE_ABORT_THRESHOLD,
                )

                caplog.clear()

                # Step 3 — raise mock spot between first sell and neighbour; force-trigger master DAG against new price path.
                first_sell_price = _first_sell_limit_price(master_reader.state.automation.exchange_account_elements)
                simulated_close["value"] = float(first_sell_price + _D_DECIMAL_INCREMENT / decimal.Decimal("2"))

                try:
                    await asyncio.wait_for(
                        octobot_node.scheduler.tasks.send_forced_trigger_to_automation(_MASTER_AUTOMATION_ID),
                        timeout=_T_STOP_SEND_SECONDS,
                    )
                except TimeoutError as exc:
                    raise AssertionError("send_forced_trigger_to_automation(master) timed out") from exc

                # Step 4 — master's ladder updates + emits; copy reacts via trading-signal inbox + ``trigger_copier_automation``.
                master_reader = await _poll_state_reader_until(
                    temp_dbos_scheduler,
                    _MASTER_AUTOMATION_ID,
                    lambda reader: _post_fill_open_order_shape(
                        *grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                            reader.state.automation.exchange_account_elements
                        )[:2],
                    ),
                    _T_POST_SHOCK_SECONDS,
                    "master post-shock ladder (3 buy, 1 sell open)",
                )

                copy_reader = await _poll_state_reader_until(
                    temp_dbos_scheduler,
                    _COPY_AUTOMATION_ID,
                    lambda reader: _post_fill_open_order_shape(
                        *grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                            reader.state.automation.exchange_account_elements
                        )[:2],
                    ),
                    _T_POST_SHOCK_SECONDS,
                    "copy post-signal ladder (3 buy, 1 sell open)",
                )

                _assert_open_limit_prices_match_reference(
                    master_reader.state.automation.exchange_account_elements,
                    copy_reader.state.automation.exchange_account_elements,
                )
                _assert_btc_usdc_value_shares_match_reference(
                    master_reader.state.automation.exchange_account_elements,
                    copy_reader.state.automation.exchange_account_elements,
                    btc_usdc_close=decimal.Decimal(str(simulated_close["value"])),
                )

                assert upload_trading_signal_mock.await_count > baseline_upload_count

                _assert_orders_synchronizer_no_mirror_cancel_or_grace_logs(caplog)

                # Step 5 — priority-stop both workflows; rely on SUCCESS + ``stop_automation`` payloads for each automation_id.
                stop_priority_action = {
                    "id": "action_stop_priority",
                    "dsl_script": "stop_automation()",
                }
                for automation_id in (_MASTER_AUTOMATION_ID, _COPY_AUTOMATION_ID):
                    try:
                        await asyncio.wait_for(
                            octobot_node.scheduler.tasks.send_actions_to_automation(
                                [stop_priority_action], automation_id
                            ),
                            timeout=_T_STOP_SEND_SECONDS,
                        )
                    except TimeoutError as exc:
                        raise AssertionError(f"send_actions_to_automation timed out for {automation_id}") from exc

                for automation_id in (_MASTER_AUTOMATION_ID, _COPY_AUTOMATION_ID):
                    final_text = await grid_sim_util.wait_for_stop_success_output(
                        temp_dbos_scheduler,
                        automation_id,
                        _T_STOP_COMPLETE_SECONDS,
                    )
                    parsed_final = grid_sim_util.parse_automation_workflow_output(final_text)
                    assert parsed_final.error is None
                    final_job = grid_sim_util.job_description_dict_from_output(parsed_final)
                    assert final_job["state"]["automation"]["post_actions"]["stop_automation"] is True

        finally:
            await trading_signals_channel_module.shutdown_internal_trading_signal_channel()
