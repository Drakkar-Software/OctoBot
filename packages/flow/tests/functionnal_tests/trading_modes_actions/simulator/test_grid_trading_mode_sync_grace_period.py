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
import octobot_commons.json_util as json_util
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_flow.jobs
import octobot_flow.entities as flow_entities
import octobot_flow.enums
import octobot_flow.logic.actions as flow_actions
import octobot_flow.repositories.exchange

import octobot_commons.dsl_interpreter.operators.re_callable_operator_mixin as re_callable_operator_mixin

import tests.functionnal_tests as functionnal_tests
import tests.functionnal_tests.trading_modes_actions.simulator.test_grid_trading_mode_action as grid_test
from tests.functionnal_tests import (
    automation_state_dict,
    copy_exchange_account_action,
    d_order_price,
    resolved_actions,
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
                    "internal_name": functionnal_tests.EXCHANGE_INTERNAL_NAME,
                },
                "auth_details": {},
                "portfolio": {
                    "unit": "USDC",
                },
            },
        },
    }


def _grace_account_copy_settings(
    *,
    missed_signals_grace_abort_threshold: typing.Optional[int] = None,
) -> copy_entities.AccountCopySettings:
    kwargs: dict = {
        "mirrored_orphan_cancel_grace_seconds": GRACE_SECONDS,
        "mirrored_orphan_grace_abort_threshold": 2,
    }
    if missed_signals_grace_abort_threshold is not None:
        kwargs["missed_signals_grace_abort_threshold"] = missed_signals_grace_abort_threshold
    return copy_entities.AccountCopySettings(**kwargs)


def grid_reference_four_order_account() -> copy_entities.Account:
    lowest_buy = grid_test.GRID_REFERENCE_LOWEST_BUY
    inc = float(grid_test.increment)
    spr = float(grid_test.spread)
    return copy_entities.Account(
        updated_at=time.time(),
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
        updated_at=time.time(),
        content=content_after_fill,
        orders=new_orders,
        positions=[],
        historical_snapshots=[reference_before],
    )


def reference_replace_highest_buy_with_sell_missed_signals_history(
    reference_before: copy_entities.Account,
) -> copy_entities.Account:
    """
    Like ``reference_replace_highest_buy_with_sell`` but prepend two empty-order snapshots (newest
    first) so the first compliant historical snapshot is at index 2 for missed-signals grace abort.
    """
    base = reference_replace_highest_buy_with_sell(reference_before)
    content_snapshot = copy_module.deepcopy(reference_before.content)
    empty_newest = copy_entities.Account(
        updated_at=time.time(),
        content=content_snapshot,
        orders=[],
        positions=[],
    )
    empty_mid = copy_entities.Account(
        updated_at=time.time() - 1.0,
        content=content_snapshot,
        orders=[],
        positions=[],
    )
    compliant = copy_module.deepcopy(reference_before)
    compliant = dataclasses.replace(compliant, updated_at=time.time() - 5.0)
    return dataclasses.replace(
        base,
        historical_snapshots=[empty_newest, empty_mid, compliant],
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
        updated_at=time.time(),
        content=content_after_fill,
        orders=new_orders,
        positions=[],
        historical_snapshots=[reference_before],
    )


def update_state_reference_account_details(
    dump: dict[str, typing.Any],
    reference_market: str,
    reference_account: copy_entities.Account,
    account_copy_settings: copy_entities.AccountCopySettings,
) -> None:
    dsl_details = flow_actions.create_copy_exchange_account_action(
        functionnal_tests.FUNCTIONAL_TEST_COPY_STRATEGY_ID,
        reference_market,
        reference_account,
        account_copy_settings,
    )
    dsl_details.id = COPY_ACTION_ID
    automation_state = flow_entities.AutomationState.from_dict(dump)
    if COPY_ACTION_ID not in automation_state.automation.actions_dag.get_actions_by_id():
        raise AssertionError(f"DAG action {COPY_ACTION_ID!r} not found")
    automation_state.upsert_automation_actions([dsl_details])
    dump["automation"]["actions_dag"]["actions"] = json_util.sanitize(
        automation_state.to_dict(include_default_values=False)["automation"]["actions_dag"]["actions"]
    )


def age_grace_started_at_in_dump(
    dump: dict[str, typing.Any],
    reference_market: str,
    reference_account: copy_entities.Account,
    account_copy_settings: copy_entities.AccountCopySettings,
    grace_seconds: float,
    margin_seconds: float = 15.0,
) -> None:
    """
    Make mirrored-orphan grace appear elapsed by setting reference Account.updated_at in the copy
    action DSL (grace start is derived from reference history + updated_at).
    """
    aged_updated_at = time.time() - grace_seconds - margin_seconds
    aged_account = dataclasses.replace(reference_account, updated_at=aged_updated_at)
    update_state_reference_account_details(
        dump, reference_market, aged_account, account_copy_settings
    )


def _open_orders_origins(dump: dict[str, typing.Any]) -> list[dict]:
    return [
        o[trading_constants.STORAGE_ORIGIN_VALUE]
        for o in dump["automation"]["exchange_account_elements"]["orders"]["open_orders"]
    ]


def _assert_copy_action_last_run_has_no_rebalance_orders(dump: dict[str, typing.Any]) -> None:
    """
    Unwrap the copy action's ReCallingOperatorResult last execution state and assert
    ``created_orders`` contains no rows tagged with REBALANCER_ORDER_TAG.
    """
    copy_result = None
    recall_name = re_callable_operator_mixin.ReCallingOperatorResult.__name__
    last_key = re_callable_operator_mixin.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY
    for action in dump["automation"]["actions_dag"]["actions"]:
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


def mutate_client_dump_simulate_early_fill_of_grid_ref_b1(
    dump: dict[str, typing.Any],
    _reference_r1: copy_entities.Account,
) -> None:
    """
    Simulate the client having already filled the mirrored ``grid_ref_b1`` buy while the embedded
    reference snapshot can still list that order as open (late-reference-fill alignment).
    Base/quote portfolio balances are adjusted using that order's amount and price (same economics
    as ``reference_replace_highest_buy_with_sell`` on the reference account).
    """
    storage = trading_constants.STORAGE_ORIGIN_VALUE
    id_col = trading_enums.ExchangeConstantsOrderColumns.ID.value
    amount_col = trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value
    price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    automation = dump["automation"]
    open_orders = automation["exchange_account_elements"]["orders"]["open_orders"]
    filled_wrapped: typing.Optional[dict] = None
    for wrapped in open_orders:
        if wrapped[storage][id_col] == "grid_ref_b1":
            filled_wrapped = wrapped
            break
    if filled_wrapped is None:
        raise AssertionError("expected open mirrored order grid_ref_b1")
    filled_origin = filled_wrapped[storage]
    fill_quantity = decimal.Decimal(str(filled_origin[amount_col]))
    fill_price = decimal.Decimal(str(filled_origin[price_col]))
    quote_spent = fill_quantity * fill_price

    automation["exchange_account_elements"]["orders"]["open_orders"] = [
        o for o in open_orders if o[storage][id_col] != "grid_ref_b1"
    ]

    content = automation["exchange_account_elements"]["portfolio"]["content"]
    base_currency = "BTC"
    quote_currency = "USDC"
    btc_entry = content.setdefault(base_currency, {})
    usdc_entry = content.setdefault(quote_currency, {})

    btc_total = decimal.Decimal(str(btc_entry.get("total", 0)))
    btc_available = decimal.Decimal(str(btc_entry.get("available", btc_total)))
    usdc_total = decimal.Decimal(str(usdc_entry.get("total", 0)))
    usdc_available = decimal.Decimal(str(usdc_entry.get("available", usdc_total)))

    btc_total += fill_quantity
    btc_available += fill_quantity
    usdc_total -= quote_spent
    usdc_available -= quote_spent

    btc_entry["total"] = float(btc_total)
    btc_entry["available"] = float(btc_available)
    usdc_entry["total"] = float(usdc_total)
    usdc_entry["available"] = float(usdc_available)

    mark_price = decimal.Decimal(str(grid_test._FIXED_BTC_USDC_CLOSE))
    value_base = btc_total * mark_price
    value_quote = usdc_total
    value_total = value_base + value_quote
    if value_total > decimal.Decimal("0"):
        btc_entry[copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = float(value_base / value_total)
        usdc_entry[copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = float(value_quote / value_total)


@pytest.mark.asyncio
async def test_grid_copy_trigger_grace_period_for_unfilled_client_order(init_action: dict):
    reference_market = "USDC"
    patched_fetch_tickers = grid_test.tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    patched_fetch_ohlcv = grid_test.fetch_ohlcv_side_effect_for_close_price(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    reference_r1 = grid_reference_four_order_account()
    settings = _grace_account_copy_settings()
    all_actions = [
        init_action,
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
        async with octobot_flow.jobs.AutomationJob(automation_state_template, [], [], {}) as job:
            await job.run()
        after_init = job.dump()

        async with octobot_flow.jobs.AutomationJob(after_init, [], [], {}) as job:
            await job.run()
        after_copy_r1 = job.dump()

    reference_r2 = reference_replace_highest_buy_with_sell(reference_r1)
    update_state_reference_account_details(after_copy_r1, reference_market, reference_r2, settings)

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
        async with octobot_flow.jobs.AutomationJob(after_copy_r1, [], [], {}) as job:
            await job.run()
        after_grace_trigger = job.dump()

    orphan_still_buy = [
        origin
        for origin in _open_orders_origins(after_grace_trigger)
        if origin[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
        and origin[trading_enums.ExchangeConstantsOrderColumns.ID.value] == "grid_ref_b1"
    ]
    assert len(orphan_still_buy) == 1


@pytest.mark.asyncio
async def test_grid_copy_missed_signals_abort_cancels_orphan_immediately(init_action: dict):
    reference_market = "USDC"
    patched_fetch_tickers = grid_test.tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    patched_fetch_ohlcv = grid_test.fetch_ohlcv_side_effect_for_close_price(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    reference_r1 = grid_reference_four_order_account()
    settings = _grace_account_copy_settings(missed_signals_grace_abort_threshold=2)
    all_actions = [
        init_action,
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
        async with octobot_flow.jobs.AutomationJob(automation_state_template, [], [], {}) as job:
            await job.run()
        after_init = job.dump()

        async with octobot_flow.jobs.AutomationJob(after_init, [], [], {}) as job:
            await job.run()
        after_copy_r1 = job.dump()

    origins_r1 = _open_orders_origins(after_copy_r1)
    assert len(origins_r1) == 4
    buy_ids_r1 = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        for origin in origins_r1
        if origin[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
    }
    assert "grid_ref_b0" in buy_ids_r1
    assert "grid_ref_b1" in buy_ids_r1
    sell_ids_r1 = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        for origin in origins_r1
        if origin[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.SELL.value
    }
    assert "grid_ref_s0" in sell_ids_r1
    assert "grid_ref_s1" in sell_ids_r1

    reference_r2 = reference_replace_highest_buy_with_sell_missed_signals_history(reference_r1)
    update_state_reference_account_details(after_copy_r1, reference_market, reference_r2, settings)

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
        async with octobot_flow.jobs.AutomationJob(after_copy_r1, [], [], {}) as job:
            await job.run()
        after_missed_abort = job.dump()

    open_ids = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        for origin in _open_orders_origins(after_missed_abort)
    }
    assert "grid_ref_b1" not in open_ids


@pytest.mark.asyncio
async def test_grid_copy_trigger_grace_period_for_early_filled_client_order(init_action: dict):
    reference_market = "USDC"
    patched_fetch_tickers = grid_test.tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    patched_fetch_ohlcv = grid_test.fetch_ohlcv_side_effect_for_close_price(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    reference_r1 = grid_reference_four_order_account()
    settings = _grace_account_copy_settings()
    all_actions = [
        init_action,
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
        async with octobot_flow.jobs.AutomationJob(automation_state_template, [], [], {}) as job:
            await job.run()
        after_init = job.dump()

        async with octobot_flow.jobs.AutomationJob(after_init, [], [], {}) as job:
            await job.run()
        after_copy_r1 = job.dump()

    mutate_client_dump_simulate_early_fill_of_grid_ref_b1(after_copy_r1, reference_r1)
    update_state_reference_account_details(after_copy_r1, reference_market, reference_r1, settings)

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
        async with octobot_flow.jobs.AutomationJob(after_copy_r1, [], [], {}) as job:
            await job.run()
        after_grace_trigger = job.dump()

    final_origins = _open_orders_origins(after_grace_trigger)
    assert len(final_origins) == 3
    open_ids = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value] for origin in final_origins
    }
    assert "grid_ref_b1" not in open_ids


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
    settings = _grace_account_copy_settings()
    all_actions = [
        init_action,
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
        async with octobot_flow.jobs.AutomationJob(automation_state_template, [], [], {}) as job:
            await job.run()
        after_init = job.dump()

        async with octobot_flow.jobs.AutomationJob(after_init, [], [], {}) as job:
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

    reference_r2 = reference_replace_highest_buy_with_sell(reference_r1)
    update_state_reference_account_details(after_copy_r1, reference_market, reference_r2, settings)

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
        async with octobot_flow.jobs.AutomationJob(after_copy_r1, [], [], {}) as job:
            await job.run()
        after_orphan_grace_started = job.dump()

    orphan_still_buy = [
        origin
        for origin in _open_orders_origins(after_orphan_grace_started)
        if origin[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
        and origin[trading_enums.ExchangeConstantsOrderColumns.ID.value] == "grid_ref_b1"
    ]
    assert len(orphan_still_buy) == 1

    age_grace_started_at_in_dump(
        after_orphan_grace_started,
        reference_market,
        reference_r2,
        settings,
        GRACE_SECONDS,
    )

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
        async with octobot_flow.jobs.AutomationJob(after_orphan_grace_started, [], [], {}) as job:
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
        init_action,
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
        async with octobot_flow.jobs.AutomationJob(automation_state_template, [], [], {}) as job:
            await job.run()
        after_init = job.dump()
        async with octobot_flow.jobs.AutomationJob(after_init, [], [], {}) as job:
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
        async with octobot_flow.jobs.AutomationJob(after_copy_r1, [], [], {}) as job:
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
    mirrored-orphan grace defers cancel of the stale mirrored buy. Then lower BTC/USDC below the
    highest mirrored buy so the client buy can fill; the next run clears the grace episode and
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
    settings = _grace_account_copy_settings()
    all_actions = [
        init_action,
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
        async with octobot_flow.jobs.AutomationJob(automation_state_template, [], [], {}) as job:
            await job.run()
        after_init = job.dump()
        async with octobot_flow.jobs.AutomationJob(after_init, [], [], {}) as job:
            await job.run()
        after_copy_r1 = job.dump()

    reference_r2 = reference_replace_highest_buy_with_sell(reference_r1)
    update_state_reference_account_details(after_copy_r1, reference_market, reference_r2, settings)

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
        async with octobot_flow.jobs.AutomationJob(after_copy_r1, [], [], {}) as job:
            await job.run()
        after_grace_started = job.dump()

    highest_buy_price = d_order_price(
        grid_test.GRID_REFERENCE_LOWEST_BUY + grid_test.increment
    )
    simulated_close["value"] = float(
        highest_buy_price - grid_test.D_INCREMENT / decimal.Decimal("2")
    )
    update_state_reference_account_details(
        after_grace_started, reference_market, reference_r2, settings
    )

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
        async with octobot_flow.jobs.AutomationJob(after_grace_started, [], [], {}) as job:
            await job.run()
        after_fill_sync = job.dump()

    _assert_copy_action_last_run_has_no_rebalance_orders(after_fill_sync)

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


@pytest.mark.asyncio
async def test_grid_copy_early_filled_client_order_grace_period_resolved_by_reference_fill_without_rebalance_orders(
    init_action: dict,
):
    """
    Like test_grid_copy_orphan_resolved_by_client_fill_without_rebalance_orders, but the mirrored
    orphan grace is triggered by an early client fill of grid_ref_b1 while the embedded reference
    is still R1. A second run with R1 unchanged leaves the grace episode active (no mirrored R2
    sell yet). The following run embeds R2 so the reference reflects the fill; sync completes
    without rebalance limits, not by lowering price to fill the client.
    """
    # --- Bootstrap: fixed market, copy the reference grid (R1) onto the client ---
    reference_market = "USDC"
    patched_fetch_tickers = grid_test.tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    patched_fetch_ohlcv = grid_test.fetch_ohlcv_side_effect_for_close_price(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    reference_r1 = grid_reference_four_order_account()
    settings = _grace_account_copy_settings()
    all_actions = [
        init_action,
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
        async with octobot_flow.jobs.AutomationJob(automation_state_template, [], [], {}) as job:
            await job.run()
        after_init = job.dump()
        async with octobot_flow.jobs.AutomationJob(after_init, [], [], {}) as job:
            await job.run()
        after_copy_r1 = job.dump()

    # --- Client filled mirrored grid_ref_b1 first; embedded reference still lists R1 (late ref) ---
    mutate_client_dump_simulate_early_fill_of_grid_ref_b1(after_copy_r1, reference_r1)
    update_state_reference_account_details(after_copy_r1, reference_market, reference_r1, settings)

    # --- Iteration n: first run after setup — grace episode starts (early fill vs reference R1) ---
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
        async with octobot_flow.jobs.AutomationJob(after_copy_r1, [], [], {}) as job:
            await job.run()
        after_grace_n = job.dump()

    # Check n: same shape as test_grid_copy_trigger_grace_period_for_early_filled_client_order
    after_grace_n_origins = _open_orders_origins(after_grace_n)
    assert len(after_grace_n_origins) == 3
    after_grace_n_open_ids = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value] for origin in after_grace_n_origins
    }
    assert "grid_ref_b1" not in after_grace_n_open_ids

    # --- Iteration n+1: re-embed reference R1 only; grace still active, no R2 mirror yet ---
    update_state_reference_account_details(after_grace_n, reference_market, reference_r1, settings)

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
        async with octobot_flow.jobs.AutomationJob(after_grace_n, [], [], {}) as job:
            await job.run()
        after_grace_n1 = job.dump()

    # Check n+1: still three opens; no premature grid_ref_s_from_b1; b1 stays off the book
    after_grace_n1_origins = _open_orders_origins(after_grace_n1)
    assert len(after_grace_n1_origins) == 3
    after_grace_n1_open_ids = {
        origin[trading_enums.ExchangeConstantsOrderColumns.ID.value] for origin in after_grace_n1_origins
    }
    assert "grid_ref_s_from_b1" not in after_grace_n1_open_ids
    assert "grid_ref_b1" not in after_grace_n1_open_ids

    # --- Iteration n+2: reference advances to R2 (fill reflected as sell); sync can complete ---
    reference_r2 = reference_replace_highest_buy_with_sell(reference_r1)
    update_state_reference_account_details(after_grace_n1, reference_market, reference_r2, settings)

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
        async with octobot_flow.jobs.AutomationJob(after_grace_n1, [], [], {}) as job:
            await job.run()
        after_resolved = job.dump()

    _assert_copy_action_last_run_has_no_rebalance_orders(after_resolved)

    # Final book: aligned with R2 — one buy, three sells including grid_ref_s_from_b1
    final_origins = _open_orders_origins(after_resolved)
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
