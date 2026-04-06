#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or
#  (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  OctoBot. If not, see <https://www.gnu.org/licenses/>.
import copy as copy_module
import dataclasses
import decimal
import time
import typing

import mock
import pytest

import octobot_commons.constants as common_constants
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchange_data as trading_exchange_data

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_flow
import octobot_flow.entities as flow_entities
import octobot_flow.enums
import octobot_flow.logic.actions as flow_actions
import octobot_flow.parsers.sanitizer as flow_sanitizer
import octobot_flow.repositories.exchange

import octobot_commons.dsl_interpreter.operators.re_callable_operator_mixin as re_callable_operator_mixin

import tests.functionnal_tests as functionnal_tests
import tests.functionnal_tests.trading_modes_actions.simulator.test_grid_trading_mode_action as grid_test
from tests.functionnal_tests import (
    automation_state_dict,
    copy_exchange_account_action,
    d_order_price,
    resolved_actions,
    set_init_action_run_mode,
)

ORDER_AMOUNT = 0.004
COPY_ACTION_ID = "action_copy_exchange_account"
GRACE_SECONDS = 5.0


@pytest.fixture
def init_action():
    return {
        "id": "action_init",
        "action": octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
        "config": {
            "automation": {
                "metadata": {
                    "automation_id": "automation_1",
                },
                "client_exchange_account_elements": {
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
                    "internal_name": functionnal_tests.EXCHANGE_INTERNAL_NAME,
                },
                "auth_details": {},
                "portfolio": {
                    "unit": "USDC",
                },
            },
        },
    }


def _grace_account_copy_settings() -> copy_entities.AccountCopySettings:
    return copy_entities.AccountCopySettings(
        mirrored_orphan_cancel_grace_seconds=GRACE_SECONDS,
        mirrored_orphan_grace_abort_threshold=2,
    )


def grid_reference_four_order_account() -> copy_entities.Account:
    lowest_buy = grid_test.GRID_REFERENCE_LOWEST_BUY
    inc = float(grid_test.increment)
    spr = float(grid_test.spread)
    return copy_entities.Account(
        content={
            "BTC": {
                common_constants.PORTFOLIO_TOTAL: decimal.Decimal("0.01"),
                common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("0.002"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
            },
            "USDC": {
                common_constants.PORTFOLIO_TOTAL: decimal.Decimal("1000"),
                common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("200"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
            },
        },
        orders=[
            grid_test._grid_reference_storage_order(
                "grid_ref_b0", trading_enums.TradeOrderSide.BUY.value, lowest_buy, ORDER_AMOUNT
            ),
            grid_test._grid_reference_storage_order(
                "grid_ref_b1", trading_enums.TradeOrderSide.BUY.value, lowest_buy + inc, ORDER_AMOUNT
            ),
            grid_test._grid_reference_storage_order(
                "grid_ref_s0", trading_enums.TradeOrderSide.SELL.value, lowest_buy + inc + spr, ORDER_AMOUNT
            ),
            grid_test._grid_reference_storage_order(
                "grid_ref_s1", trading_enums.TradeOrderSide.SELL.value, lowest_buy + inc + spr + inc, ORDER_AMOUNT
            ),
        ],
        positions=[],
    )


def reference_replace_highest_buy_with_sell(
    reference_before: copy_entities.Account,
) -> copy_entities.Account:
    """
    Remove the highest limit buy (grid_ref_b1), which is closest to the market and fills first,
    and add the grid-equivalent sell one spread above that buy price.
    """
    lowest_buy = grid_test.GRID_REFERENCE_LOWEST_BUY
    inc = float(grid_test.increment)
    spr = float(grid_test.spread)
    highest_buy_price = lowest_buy + inc
    new_sell_price = highest_buy_price + spr
    new_orders: list = []
    for order_doc in reference_before.orders:
        origin = order_doc[trading_constants.STORAGE_ORIGIN_VALUE]
        if origin[trading_enums.ExchangeConstantsOrderColumns.ID.value] == "grid_ref_b1":
            continue
        new_orders.append(order_doc)
    new_orders.append(
        grid_test._grid_reference_storage_order(
            "grid_ref_s_from_b1",
            trading_enums.TradeOrderSide.SELL.value,
            new_sell_price,
            ORDER_AMOUNT,
        )
    )
    content_after_fill = copy_module.deepcopy(reference_before.content)
    fill_quantity = decimal.Decimal(str(ORDER_AMOUNT))
    fill_price = decimal.Decimal(str(highest_buy_price))
    quote_spent = fill_quantity * fill_price
    btc_holdings = content_after_fill["BTC"]
    usdc_holdings = content_after_fill["USDC"]
    btc_holdings[common_constants.PORTFOLIO_TOTAL] = (
        btc_holdings[common_constants.PORTFOLIO_TOTAL] + fill_quantity
    )
    btc_holdings[common_constants.PORTFOLIO_AVAILABLE] = (
        btc_holdings[common_constants.PORTFOLIO_AVAILABLE] + fill_quantity
    )
    usdc_holdings[common_constants.PORTFOLIO_TOTAL] = (
        usdc_holdings[common_constants.PORTFOLIO_TOTAL] - quote_spent
    )
    mark_price = decimal.Decimal(str(grid_test._FIXED_BTC_USDC_CLOSE))
    btc_total_after = btc_holdings[common_constants.PORTFOLIO_TOTAL]
    usdc_total_after = usdc_holdings[common_constants.PORTFOLIO_TOTAL]
    value_btc = btc_total_after * mark_price
    value_quote = usdc_total_after
    value_total = value_btc + value_quote
    if value_total > decimal.Decimal("0"):
        btc_holdings[copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = (
            value_btc / value_total
        )
        usdc_holdings[copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = (
            value_quote / value_total
        )
    return copy_entities.Account(
        content=content_after_fill,
        orders=new_orders,
        positions=[],
    )


def reference_replace_both_buys_with_sells(
    reference_before: copy_entities.Account,
) -> copy_entities.Account:
    lowest_buy = grid_test.GRID_REFERENCE_LOWEST_BUY
    inc = float(grid_test.increment)
    spr = float(grid_test.spread)
    new_orders: list = []
    for order_doc in reference_before.orders:
        origin = order_doc[trading_constants.STORAGE_ORIGIN_VALUE]
        oid = origin[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        if oid in ("grid_ref_b0", "grid_ref_b1"):
            continue
        new_orders.append(order_doc)
    new_orders.append(
        grid_test._grid_reference_storage_order(
            "grid_ref_s_fill_b0",
            trading_enums.TradeOrderSide.SELL.value,
            lowest_buy + spr,
            ORDER_AMOUNT,
        )
    )
    new_orders.append(
        grid_test._grid_reference_storage_order(
            "grid_ref_s_fill_b1",
            trading_enums.TradeOrderSide.SELL.value,
            lowest_buy + inc + spr,
            ORDER_AMOUNT,
        )
    )
    content_after_fill = copy_module.deepcopy(reference_before.content)
    fill_quantity = decimal.Decimal(str(ORDER_AMOUNT))
    lowest_buy_price = decimal.Decimal(str(lowest_buy))
    inc_decimal = decimal.Decimal(str(inc))
    quote_spent = fill_quantity * (2 * lowest_buy_price + inc_decimal)
    btc_holdings = content_after_fill["BTC"]
    usdc_holdings = content_after_fill["USDC"]
    btc_received = fill_quantity * decimal.Decimal("2")
    btc_holdings[common_constants.PORTFOLIO_TOTAL] = (
        btc_holdings[common_constants.PORTFOLIO_TOTAL] + btc_received
    )
    btc_holdings[common_constants.PORTFOLIO_AVAILABLE] = (
        btc_holdings[common_constants.PORTFOLIO_AVAILABLE] + btc_received
    )
    usdc_holdings[common_constants.PORTFOLIO_TOTAL] = (
        usdc_holdings[common_constants.PORTFOLIO_TOTAL] - quote_spent
    )
    mark_price = decimal.Decimal(str(grid_test._FIXED_BTC_USDC_CLOSE))
    btc_total_after = btc_holdings[common_constants.PORTFOLIO_TOTAL]
    usdc_total_after = usdc_holdings[common_constants.PORTFOLIO_TOTAL]
    value_btc = btc_total_after * mark_price
    value_quote = usdc_total_after
    pair_value_total = value_btc + value_quote
    if pair_value_total > decimal.Decimal("0"):
        btc_holdings[copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = (
            value_btc / pair_value_total
        )
        usdc_holdings[copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = (
            value_quote / pair_value_total
        )
    return copy_entities.Account(
        content=content_after_fill,
        orders=new_orders,
        positions=[],
    )


def update_state_reference_account_details(
    dump: dict[str, typing.Any],
    reference_market: str,
    reference_account: copy_entities.Account,
    account_copy_settings: copy_entities.AccountCopySettings,
) -> None:
    grace_started_at = dump["automation"]["execution"]["copy_details"].get(
        "open_orders_grace_period_started_at"
    )
    settings_with_grace = dataclasses.replace(
        account_copy_settings,
        mirrored_orphan_grace_started_at=grace_started_at,
    )
    dsl_details = flow_actions.create_copy_exchange_account_action(
        reference_market, reference_account, settings_with_grace
    )
    dsl_details.id = COPY_ACTION_ID
    automation_state = flow_entities.AutomationState.from_dict(dump)
    if COPY_ACTION_ID not in automation_state.automation.actions_dag.get_actions_by_id():
        raise AssertionError(f"DAG action {COPY_ACTION_ID!r} not found")
    automation_state.upsert_automation_actions([dsl_details])
    dump["automation"]["actions_dag"]["actions"] = flow_sanitizer.sanitize(
        automation_state.to_dict(include_default_values=False)["automation"]["actions_dag"]["actions"]
    )


def age_grace_started_at_in_dump(
    dump: dict[str, typing.Any],
    grace_seconds: float,
    margin_seconds: float = 15.0,
) -> None:
    path = dump["automation"]["execution"]["copy_details"]
    path["open_orders_grace_period_started_at"] = time.time() - grace_seconds - margin_seconds


def _open_orders_origins(dump: dict[str, typing.Any]) -> list[dict]:
    return [
        o[trading_constants.STORAGE_ORIGIN_VALUE]
        for o in dump["automation"]["client_exchange_account_elements"]["orders"]["open_orders"]
    ]


def _orders_by_side_with_id(origins: list[dict], side: str) -> list[tuple[str, float]]:
    price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    id_col = trading_enums.ExchangeConstantsOrderColumns.ID.value
    side_col = trading_enums.ExchangeConstantsOrderColumns.SIDE.value
    return sorted(
        [
            (o[id_col], float(o[price_col]))
            for o in origins
            if o[side_col] == side
        ],
        key=lambda row: row[1],
    )


@pytest.mark.asyncio
async def test_grid_copy_grace_elapses_then_orphan_cancelled_and_sell_mirrored(init_action: dict):
    reference_market = "USDC"
    patched_fetch_tickers = grid_test.tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    patched_fetch_ohlcv = grid_test.fetch_ohlcv_side_effect_for_close_price(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    reference_r1 = grid_reference_four_order_account()
    reference_r2 = reference_replace_highest_buy_with_sell(reference_r1)
    settings = _grace_account_copy_settings()
    all_actions = [
        set_init_action_run_mode(init_action, octobot_flow.enums.AutomationRunMode.UPDATE_CLIENT_EXCHANGE_ACCOUNT_ONLY),
        copy_exchange_account_action(reference_market, reference_r1, settings),
    ]
    automation_state_template = automation_state_dict(resolved_actions(all_actions))
    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        async with octobot_flow.AutomationJob(automation_state_template, [], {}) as job:
            await job.run()
        after_init = job.dump()

        async with octobot_flow.AutomationJob(after_init, [], {}) as job:
            await job.run()
        after_copy_r1 = job.dump()

    for action in after_copy_r1["automation"]["actions_dag"]["actions"]:
        assert isinstance(action, dict)
        if action.get("id") == "action_init":
            assert action.get("executed_at")
        elif action.get("id") == COPY_ACTION_ID:
            assert action.get("executed_at") is None
            assert isinstance(action.get("previous_execution_result"), dict)

    origins_r1 = _open_orders_origins(after_copy_r1)
    buy_ids_r1 = {origin[trading_enums.ExchangeConstantsOrderColumns.ID.value] for origin in origins_r1 if origin[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value}
    assert "grid_ref_b0" in buy_ids_r1
    assert "grid_ref_b1" in buy_ids_r1

    update_state_reference_account_details(after_copy_r1, reference_market, reference_r2, settings)

    trading_exchange_data.TickerUpdater.reset_cache()
    trading_exchange_data.OHLCVUpdater.reset_cache()

    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        async with octobot_flow.AutomationJob(after_copy_r1, [], {}) as job:
            await job.run()
        after_orphan_grace_started = job.dump()

    grace_at = after_orphan_grace_started["automation"]["execution"]["copy_details"][
        "open_orders_grace_period_started_at"
    ]
    assert grace_at is not None
    orphan_still_buy = [
        origin
        for origin in _open_orders_origins(after_orphan_grace_started)
        if origin[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
        and origin[trading_enums.ExchangeConstantsOrderColumns.ID.value] == "grid_ref_b1"
    ]
    assert len(orphan_still_buy) == 1

    age_grace_started_at_in_dump(after_orphan_grace_started, GRACE_SECONDS)
    # also update the grace started at in copy action dsl
    update_state_reference_account_details(after_orphan_grace_started, reference_market, reference_r2, settings)

    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        async with octobot_flow.AutomationJob(after_orphan_grace_started, [], {}) as job:
            await job.run()
        after_grace_elapsed = job.dump()

    final_origins = _open_orders_origins(after_grace_elapsed)
    buy_ids_final = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        for origin in final_origins
        if origin[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
    }
    assert len(buy_ids_final) == 1
    assert "grid_ref_b1" not in buy_ids_final
    sell_pairs = _orders_by_side_with_id(final_origins, trading_enums.TradeOrderSide.SELL.value)
    sell_ids = {row[0] for row in sell_pairs}
    assert len(sell_ids) == 3
    assert "grid_ref_s_from_b1" in sell_ids


@pytest.mark.asyncio
async def test_grid_copy_grace_aborted_when_second_orphan_exceeds_threshold(init_action: dict):
    reference_market = "USDC"
    patched_fetch_tickers = grid_test.tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    patched_fetch_ohlcv = grid_test.fetch_ohlcv_side_effect_for_close_price(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    reference_r1 = grid_reference_four_order_account()
    reference_r2 = reference_replace_both_buys_with_sells(reference_r1)
    settings = _grace_account_copy_settings()
    all_actions = [
        set_init_action_run_mode(init_action, octobot_flow.enums.AutomationRunMode.UPDATE_CLIENT_EXCHANGE_ACCOUNT_ONLY),
        copy_exchange_account_action(reference_market, reference_r1, settings),
    ]
    automation_state_template = automation_state_dict(resolved_actions(all_actions))
    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        async with octobot_flow.AutomationJob(automation_state_template, [], {}) as job:
            await job.run()
        after_init = job.dump()
        async with octobot_flow.AutomationJob(after_init, [], {}) as job:
            await job.run()
        after_copy_r1 = job.dump()

    buy_ids = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        for origin in _open_orders_origins(after_copy_r1)
        if origin[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
    }
    assert "grid_ref_b0" in buy_ids
    assert "grid_ref_b1" in buy_ids

    update_state_reference_account_details(after_copy_r1, reference_market, reference_r2, settings)
    now = time.time()
    after_copy_r1["automation"]["execution"]["copy_details"]["open_orders_grace_period_started_at"] = (
        now - GRACE_SECONDS + 1.0
    )

    trading_exchange_data.TickerUpdater.reset_cache()
    trading_exchange_data.OHLCVUpdater.reset_cache()

    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        async with octobot_flow.AutomationJob(after_copy_r1, [], {}) as job:
            await job.run()
        after_threshold = job.dump()

    final_origins = _open_orders_origins(after_threshold)
    buy_ids_final = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        for origin in final_origins
        if origin[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
    }
    assert len(buy_ids_final) == 0
    sell_ids = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        for origin in final_origins
        if origin[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.SELL.value
    }
    assert len(sell_ids) == 4
    assert "grid_ref_s_fill_b0" in sell_ids
    assert "grid_ref_s_fill_b1" in sell_ids


@pytest.mark.asyncio
async def test_grid_copy_orphan_resolved_by_client_fill_without_rebalance_orders(init_action: dict):
    """
    After copying the reference grid, switch the embedded reference to R2 at the original close:
    first automation run starts an open-order grace period (``open_orders_grace_period_started_at``
    is set). Then lower BTC/USDC below the highest mirrored buy (midway between the two bid
    rungs) so the client buy can fill; the second run clears grace (``started_at`` is None) and
    mirrors the new reference sell without rebalance limit creations.
    """
    reference_market = "USDC"
    simulated_close = {"value": float(grid_test._FIXED_BTC_USDC_CLOSE)}
    patched_fetch_tickers = grid_test.tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: simulated_close["value"]
    )
    patched_fetch_ohlcv = grid_test.fetch_ohlcv_side_effect_for_close_price(
        lambda: simulated_close["value"]
    )
    reference_r1 = grid_reference_four_order_account()
    reference_r2 = reference_replace_highest_buy_with_sell(reference_r1)
    settings = _grace_account_copy_settings()
    all_actions = [
        set_init_action_run_mode(init_action, octobot_flow.enums.AutomationRunMode.UPDATE_CLIENT_EXCHANGE_ACCOUNT_ONLY),
        copy_exchange_account_action(reference_market, reference_r1, settings),
    ]
    automation_state_template = automation_state_dict(resolved_actions(all_actions))
    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        async with octobot_flow.AutomationJob(automation_state_template, [], {}) as job:
            await job.run()
        after_init = job.dump()
        async with octobot_flow.AutomationJob(after_init, [], {}) as job:
            await job.run()
        after_copy_r1 = job.dump()

    update_state_reference_account_details(after_copy_r1, reference_market, reference_r2, settings)

    trading_exchange_data.TickerUpdater.reset_cache()
    trading_exchange_data.OHLCVUpdater.reset_cache()

    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        async with octobot_flow.AutomationJob(after_copy_r1, [], {}) as job:
            await job.run()
        after_grace_started = job.dump()

    grace_started_at = after_grace_started["automation"]["execution"]["copy_details"][
        "open_orders_grace_period_started_at"
    ]
    assert grace_started_at is not None

    highest_buy_price = d_order_price(
        grid_test.GRID_REFERENCE_LOWEST_BUY + grid_test.increment
    )
    simulated_close["value"] = float(
        highest_buy_price - grid_test.D_INCREMENT / decimal.Decimal("2")
    )
    update_state_reference_account_details(
        after_grace_started, reference_market, reference_r2, settings
    )

    trading_exchange_data.TickerUpdater.reset_cache()
    trading_exchange_data.OHLCVUpdater.reset_cache()

    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        async with octobot_flow.AutomationJob(after_grace_started, [], {}) as job:
            await job.run()
        after_fill_sync = job.dump()

    assert (
        after_fill_sync["automation"]["execution"]["copy_details"][
            "open_orders_grace_period_started_at"
        ]
        is None
    )

    copy_result = None
    recall_name = re_callable_operator_mixin.ReCallingOperatorResult.__name__
    last_key = re_callable_operator_mixin.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY
    for action in after_fill_sync["automation"]["actions_dag"]["actions"]:
        if action.get("id") != COPY_ACTION_ID:
            continue
        result = action.get("result") or action.get("previous_execution_result")
        if not result:
            continue
        if not isinstance(result, dict) or recall_name not in result:
            continue
        recall = result[recall_name]
        if isinstance(recall, dict):
            last = recall.get(last_key)
            if isinstance(last, dict):
                copy_result = last.get("state")
        break

    created_raw: list = []
    if isinstance(copy_result, dict):
        created_raw = copy_result.get("created_orders") or []

    tag_col = trading_enums.ExchangeConstantsOrderColumns.TAG.value
    limit_rebalance_like = [
        row
        for row in created_raw
        if isinstance(row, dict) and row.get(tag_col) == copy_constants.REBALANCER_ORDER_TAG
    ]
    assert len(limit_rebalance_like) == 0

    final_origins = _open_orders_origins(after_fill_sync)
    side_col = trading_enums.ExchangeConstantsOrderColumns.SIDE.value
    buy_origins = [
        origin
        for origin in final_origins
        if origin[side_col] == trading_enums.TradeOrderSide.BUY.value
    ]
    sell_origins = [
        origin
        for origin in final_origins
        if origin[side_col] == trading_enums.TradeOrderSide.SELL.value
    ]
    assert len(buy_origins) == 1
    assert len(sell_origins) == 3
    sell_ids = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        for origin in sell_origins
    }
    assert "grid_ref_s_from_b1" in sell_ids
