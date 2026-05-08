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
import decimal
import importlib.util
import pathlib
import time

import pytest

import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_copy.constants as copy_constants
import octobot_copy.copiers.account_copier_factory as account_copier_factory
import octobot_copy.entities as copy_entities
import octobot_copy.enums as copy_enums
import octobot_protocol.models as protocol_models


def _load_copy_tests_python_helpers():
    init_path = pathlib.Path(__file__).resolve().parent.parent / "__init__.py"
    spec = importlib.util.spec_from_file_location("copy_tests_python_helpers", init_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


copy_tests_python_helpers = _load_copy_tests_python_helpers()

pytestmark = pytest.mark.asyncio

_BTC_USDT = "BTC/USDT"
_ETH_USDT = "ETH/USDT"
_ADA_USDT = "ADA/USDT"


def _copied_reference_account(
    *assets: tuple[str, float, float],
) -> protocol_models.CopiedAccount:
    """Build a CopiedAccount from (name, spot_amount, ratio) rows; spot_amount is both total and available."""
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=time.time(),
        copied_assets=[
            protocol_models.CopiedAsset(name=name, total=value, available=value, ratio=ratio)
            for name, value, ratio in assets
        ],
        orders=[],
    )


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=True)
async def test_rebalance_plan_and_execution_70_30_to_50_50_btc_usdt_optimized_path(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    copy_tests_python_helpers.ensure_traded_symbol_pairs(exchange_manager, (_BTC_USDT,))
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    btc_usdt_price = decimal.Decimal("50000")
    total_portfolio_usdt = decimal.Decimal("80000")
    usdt_total = total_portfolio_usdt * decimal.Decimal("0.3")
    btc_value_usdt = total_portfolio_usdt * decimal.Decimal("0.7")
    btc_quantity = btc_value_usdt / btc_usdt_price

    trading_api.force_set_mark_price(exchange_manager, _BTC_USDT, btc_usdt_price)
    portfolio_manager.portfolio.update_portfolio_from_balance(
        {
            "BTC": {"available": btc_quantity, "total": btc_quantity},
            "USDT": {"available": usdt_total, "total": usdt_total},
        },
        True,
    )
    portfolio_manager.handle_balance_updated()
    portfolio_manager.portfolio_value_holder.value_converter.missing_currency_data_in_exchange.discard("USDT")
    portfolio_manager.handle_mark_price_update(_BTC_USDT, btc_usdt_price)

    reference_account = _copied_reference_account(
        ("BTC", 1.0, 0.5),
        ("USDT", 1.0, 0.5),
    )
    copy_settings = copy_entities.AccountCopySettings()
    copier = account_copier_factory.create_account_copier(
        reference_account,
        copy_settings,
        exchange_manager,
        copier_trading_mode=None,
    )

    _rebalancer, should_rebalance, details = await copier._prepare_rebalance_plan()
    assert should_rebalance is True
    assert details == {
        copy_enums.RebalanceDetails.FORCED_REBALANCE.value: False,
        copy_enums.RebalanceDetails.SELL_SOME.value: {"BTC": decimal.Decimal("0.5")},
        copy_enums.RebalanceDetails.BUY_MORE.value: {"USDT": decimal.Decimal("0.5")},
        copy_enums.RebalanceDetails.SWAP.value: {},
        copy_enums.RebalanceDetails.REMOVE.value: {},
        copy_enums.RebalanceDetails.ADD.value: {},
    }

    result = await copier.copy_account()
    # Two-asset spot: single partial sell (delta to target); no full round-trip.
    rebalance_orders = result.created_orders
    assert len(rebalance_orders) == 1

    sell_orders = [
        order
        for order in rebalance_orders
        if order.symbol == _BTC_USDT and order.side is trading_enums.TradeOrderSide.SELL
    ]
    buy_orders = [
        order
        for order in rebalance_orders
        if order.symbol == _BTC_USDT and order.side is trading_enums.TradeOrderSide.BUY
    ]
    assert len(sell_orders) == 1
    assert len(buy_orders) == 0
    expected_sell_delta = btc_quantity - (total_portfolio_usdt * decimal.Decimal("0.5")) / btc_usdt_price
    assert sell_orders[0].origin_quantity == expected_sell_delta == decimal.Decimal("0.32")
    assert sell_orders[0].origin_price == btc_usdt_price


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=True)
async def test_rebalance_plan_and_execution_20_80_to_50_50_btc_usdt_optimized_path(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    copy_tests_python_helpers.ensure_traded_symbol_pairs(exchange_manager, (_BTC_USDT,))
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    btc_usdt_price = decimal.Decimal("50000")
    total_portfolio_usdt = decimal.Decimal("100000")
    usdt_total = total_portfolio_usdt * decimal.Decimal("0.8")
    btc_value_usdt = total_portfolio_usdt * decimal.Decimal("0.2")
    btc_quantity = btc_value_usdt / btc_usdt_price

    trading_api.force_set_mark_price(exchange_manager, _BTC_USDT, btc_usdt_price)
    portfolio_manager.portfolio.update_portfolio_from_balance(
        {
            "BTC": {"available": btc_quantity, "total": btc_quantity},
            "USDT": {"available": usdt_total, "total": usdt_total},
        },
        True,
    )
    portfolio_manager.handle_balance_updated()
    portfolio_manager.portfolio_value_holder.value_converter.missing_currency_data_in_exchange.discard("USDT")
    portfolio_manager.handle_mark_price_update(_BTC_USDT, btc_usdt_price)

    reference_account = _copied_reference_account(
        ("BTC", 1.0, 0.5),
        ("USDT", 1.0, 0.5),
    )
    copy_settings = copy_entities.AccountCopySettings()
    copier = account_copier_factory.create_account_copier(
        reference_account,
        copy_settings,
        exchange_manager,
        copier_trading_mode=None,
    )

    _rebalancer, should_rebalance, details = await copier._prepare_rebalance_plan()
    assert should_rebalance is True
    assert details == {
        copy_enums.RebalanceDetails.FORCED_REBALANCE.value: False,
        copy_enums.RebalanceDetails.SELL_SOME.value: {"USDT": decimal.Decimal("0.5")},
        copy_enums.RebalanceDetails.BUY_MORE.value: {"BTC": decimal.Decimal("0.5")},
        copy_enums.RebalanceDetails.SWAP.value: {},
        copy_enums.RebalanceDetails.REMOVE.value: {},
        copy_enums.RebalanceDetails.ADD.value: {},
    }

    result = await copier.copy_account()
    rebalance_orders = result.created_orders
    assert len(rebalance_orders) == 1
    buy_orders = [
        order
        for order in rebalance_orders
        if order.symbol == _BTC_USDT and order.side is trading_enums.TradeOrderSide.BUY
    ]
    sell_orders = [
        order
        for order in rebalance_orders
        if order.symbol == _BTC_USDT and order.side is trading_enums.TradeOrderSide.SELL
    ]
    assert len(buy_orders) == 1
    assert len(sell_orders) == 0
    target_btc = (total_portfolio_usdt * decimal.Decimal("0.5")) / btc_usdt_price
    expected_buy_delta = target_btc - btc_quantity
    assert buy_orders[0].origin_quantity == expected_buy_delta == decimal.Decimal("0.6")
    assert buy_orders[0].origin_price == btc_usdt_price


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=True)
async def test_rebalance_plan_and_execution_two_asset_dust_falls_back_to_full_sell_and_buy(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    copy_tests_python_helpers.ensure_traded_symbol_pairs(exchange_manager, (_BTC_USDT,))
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    btc_usdt_price = decimal.Decimal("50000")
    # Small portfolio so delta-to-target is below min order size: efficient path bails out, legacy runs.
    total_portfolio_usdt = decimal.Decimal("10")
    btc_ratio = decimal.Decimal("0.51") # 1% above target
    usdt_total = total_portfolio_usdt * (trading_constants.ONE - btc_ratio)
    btc_value_usdt = total_portfolio_usdt * btc_ratio
    btc_quantity = btc_value_usdt / btc_usdt_price

    trading_api.force_set_mark_price(exchange_manager, _BTC_USDT, btc_usdt_price)
    portfolio_manager.portfolio.update_portfolio_from_balance(
        {
            "BTC": {"available": btc_quantity, "total": btc_quantity},
            "USDT": {"available": usdt_total, "total": usdt_total},
        },
        True,
    )
    portfolio_manager.handle_balance_updated()
    portfolio_manager.portfolio_value_holder.value_converter.missing_currency_data_in_exchange.discard("USDT")
    portfolio_manager.handle_mark_price_update(_BTC_USDT, btc_usdt_price)

    reference_account = _copied_reference_account(
        ("BTC", 1.0, 0.5),
        ("USDT", 1.0, 0.5),
    )
    copy_settings = copy_entities.AccountCopySettings(
        rebalance_trigger_min_ratio=decimal.Decimal("0"),
    )
    copier = account_copier_factory.create_account_copier(
        reference_account,
        copy_settings,
        exchange_manager,
        copier_trading_mode=None,
    )

    _rebalancer, should_rebalance, details = await copier._prepare_rebalance_plan()
    assert should_rebalance is True

    result = await copier.copy_account()
    rebalance_orders = result.created_orders
    assert len(rebalance_orders) == 2
    assert {order.symbol for order in rebalance_orders} == {_BTC_USDT}
    assert any(order.side is trading_enums.TradeOrderSide.SELL for order in rebalance_orders)
    assert any(order.side is trading_enums.TradeOrderSide.BUY for order in rebalance_orders)


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=True)
async def test_rebalance_plan_and_execution_80_btc_20_eth_to_50_btc_50_ada(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    copy_tests_python_helpers.ensure_traded_symbol_pairs(
        exchange_manager,
        (_BTC_USDT, _ETH_USDT, _ADA_USDT),
    )
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    btc_usdt_price = decimal.Decimal("50000")
    eth_usdt_price = decimal.Decimal("2500")
    ada_usdt_price = decimal.Decimal("0.5")
    total_portfolio_usdt = decimal.Decimal("100000")
    btc_value_usdt = total_portfolio_usdt * decimal.Decimal("0.8")
    eth_value_usdt = total_portfolio_usdt * decimal.Decimal("0.2")
    btc_quantity = btc_value_usdt / btc_usdt_price
    eth_quantity = eth_value_usdt / eth_usdt_price

    trading_api.force_set_mark_price(exchange_manager, _BTC_USDT, btc_usdt_price)
    trading_api.force_set_mark_price(exchange_manager, _ETH_USDT, eth_usdt_price)
    trading_api.force_set_mark_price(exchange_manager, _ADA_USDT, ada_usdt_price)
    portfolio_manager.portfolio.update_portfolio_from_balance(
        {
            "BTC": {"available": btc_quantity, "total": btc_quantity},
            "ETH": {"available": eth_quantity, "total": eth_quantity},
        },
        True,
    )
    portfolio_manager.handle_balance_updated()
    portfolio_manager.portfolio_value_holder.value_converter.missing_currency_data_in_exchange.discard("USDT")
    portfolio_manager.handle_mark_price_update(_BTC_USDT, btc_usdt_price)
    portfolio_manager.handle_mark_price_update(_ETH_USDT, eth_usdt_price)
    portfolio_manager.handle_mark_price_update(_ADA_USDT, ada_usdt_price)

    reference_account = _copied_reference_account(
        ("ADA", 1.0, 0.5),
        ("BTC", 1.0, 0.5),
    )
    copy_settings = copy_entities.AccountCopySettings()
    copier = account_copier_factory.create_account_copier(
        reference_account,
        copy_settings,
        exchange_manager,
        copier_trading_mode=None,
    )

    _rebalancer, should_rebalance, details = await copier._prepare_rebalance_plan()
    assert should_rebalance is True
    assert details == {
        copy_enums.RebalanceDetails.FORCED_REBALANCE.value: False,
        copy_enums.RebalanceDetails.SELL_SOME.value: {"BTC": decimal.Decimal("0.5")},
        copy_enums.RebalanceDetails.BUY_MORE.value: {},
        copy_enums.RebalanceDetails.SWAP.value: {},
        copy_enums.RebalanceDetails.REMOVE.value: {"ETH": decimal.Decimal("0.2")},
        copy_enums.RebalanceDetails.ADD.value: {"ADA": decimal.Decimal("0.5")},
    }

    result = await copier.copy_account()
    rebalance_orders = result.created_orders
    assert len(rebalance_orders) == 4

    sell_symbols = {
        order.symbol
        for order in rebalance_orders
        if order.side is trading_enums.TradeOrderSide.SELL
    }
    buy_symbols = {
        order.symbol
        for order in rebalance_orders
        if order.side is trading_enums.TradeOrderSide.BUY
    }
    assert sell_symbols == {_BTC_USDT, _ETH_USDT}
    assert buy_symbols == {_BTC_USDT, _ADA_USDT}


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=True)
async def test_rebalance_plan_and_execution_100_usdt_to_50_btc_50_eth(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    copy_tests_python_helpers.ensure_traded_symbol_pairs(
        exchange_manager,
        (_BTC_USDT, _ETH_USDT),
    )
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    btc_usdt_price = decimal.Decimal("50000")
    eth_usdt_price = decimal.Decimal("3000")
    usdt_total = decimal.Decimal("100000")

    trading_api.force_set_mark_price(exchange_manager, _BTC_USDT, btc_usdt_price)
    trading_api.force_set_mark_price(exchange_manager, _ETH_USDT, eth_usdt_price)
    portfolio_manager.portfolio.update_portfolio_from_balance(
        {
            "USDT": {"available": usdt_total, "total": usdt_total},
        },
        True,
    )
    portfolio_manager.handle_balance_updated()
    portfolio_manager.portfolio_value_holder.value_converter.missing_currency_data_in_exchange.discard("USDT")
    portfolio_manager.handle_mark_price_update(_BTC_USDT, btc_usdt_price)
    portfolio_manager.handle_mark_price_update(_ETH_USDT, eth_usdt_price)

    reference_account = _copied_reference_account(
        ("BTC", 1.0, 0.5),
        ("ETH", 1.0, 0.5),
    )
    copy_settings = copy_entities.AccountCopySettings()
    copier = account_copier_factory.create_account_copier(
        reference_account,
        copy_settings,
        exchange_manager,
        copier_trading_mode=None,
    )

    _rebalancer, should_rebalance, details = await copier._prepare_rebalance_plan()
    assert should_rebalance is True
    assert details == {
        copy_enums.RebalanceDetails.FORCED_REBALANCE.value: False,
        copy_enums.RebalanceDetails.SELL_SOME.value: {},
        copy_enums.RebalanceDetails.BUY_MORE.value: {},
        copy_enums.RebalanceDetails.SWAP.value: {},
        copy_enums.RebalanceDetails.REMOVE.value: {},
        copy_enums.RebalanceDetails.ADD.value: {
            "BTC": decimal.Decimal("0.5"),
            "ETH": decimal.Decimal("0.5"),
        },
    }

    result = await copier.copy_account()
    rebalance_orders = result.created_orders
    assert len(rebalance_orders) == 2
    assert {order.symbol for order in rebalance_orders} == {_BTC_USDT, _ETH_USDT}
    assert all(order.side is trading_enums.TradeOrderSide.BUY for order in rebalance_orders)
