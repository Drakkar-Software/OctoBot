#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import mock
import pytest
import decimal

import octobot_commons.signals as commons_signals
import octobot_commons.asyncio_tools as asyncio_tools

import octobot_trading.constants as constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as errors
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.modes.modes_util as modes_util
import octobot_trading.signals as signals

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_get_assets_requiring_extra_price_data_to_convert(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    assert modes_util.get_assets_requiring_extra_price_data_to_convert(exchange_manager, [], "USDT") == set()
    assert modes_util.get_assets_requiring_extra_price_data_to_convert(exchange_manager, ["BTC", "ETH"], "USDT") == {
        "BTC"
    }
    converter = exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter
    converter.update_last_price("BTC/USDT", decimal.Decimal(1))
    # no ETH in portfolio
    assert modes_util.get_assets_requiring_extra_price_data_to_convert(exchange_manager, ["BTC", "ETH"], "USDT") \
           == set()
    # same when no backtesting
    exchange_manager.is_backtesting = False
    assert modes_util.get_assets_requiring_extra_price_data_to_convert(exchange_manager, ["BTC", "ETH"], "USDT") \
           == set()
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio["ETH"] = \
        trading_personal_data.Asset("ETH", constants.ONE, constants.ONE)
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio["SOL"] = \
        trading_personal_data.Asset("SOL", constants.ONE, constants.ONE)
    # ETH in portfolio
    assert sorted(list(modes_util.get_assets_requiring_extra_price_data_to_convert(
        exchange_manager, ["BTC", "ETH", "SOL"], "USDT"
    ))) == sorted(list({'ETH', 'SOL'}))
    converter.update_last_price("BTC/ETH", decimal.Decimal(2))
    # can bridge ETH price using BTC
    assert modes_util.get_assets_requiring_extra_price_data_to_convert(exchange_manager, ["BTC", "ETH"], "USDT") \
           == set()
    exchange_manager.is_backtesting = True
    assert modes_util.get_assets_requiring_extra_price_data_to_convert(exchange_manager, ["BTC", "ETH"], "USDT") \
           == set()


async def test_convert_assets_to_target_asset():
    trading_mode = "trading_mode"
    sellable_assets = ["USDT", "PLOP"]
    target_asset = "USD"
    tickers = {"BTC/USDT": {}}
    with mock.patch.object(
            modes_util, "convert_asset_to_target_asset", mock.AsyncMock(return_value=["orders"])
    ) as convert_asset_to_target_asset:
        orders = \
            await modes_util.convert_assets_to_target_asset(trading_mode, sellable_assets, target_asset, tickers)

        assert convert_asset_to_target_asset.call_count == 2
        assert convert_asset_to_target_asset.mock_calls[0].args == \
               (trading_mode, "PLOP", target_asset, {"BTC/USDT": {}})
        assert convert_asset_to_target_asset.mock_calls[0].kwargs == {"asset_amount": None, "dependencies": None}
        assert convert_asset_to_target_asset.mock_calls[1].args == \
               (trading_mode, "USDT", target_asset, {"BTC/USDT": {}})
        assert convert_asset_to_target_asset.mock_calls[1].kwargs == {"asset_amount": None, "dependencies": None}

        assert orders == ["orders", "orders"]

        convert_asset_to_target_asset.reset_mock()
        orders = await modes_util.convert_assets_to_target_asset(trading_mode, [], target_asset, {"tickers": {}})
        convert_asset_to_target_asset.assert_not_called()
        assert orders == []

    with mock.patch.object(
        modes_util, "convert_asset_to_target_asset", mock.AsyncMock(side_effect=KeyError)
    ) as convert_asset_to_target_asset:
        trading_mode = mock.Mock()
        assert await modes_util.convert_assets_to_target_asset(
            trading_mode, sellable_assets, target_asset, tickers,
            dependencies=signals.get_orders_dependencies([
                mock.Mock(order_id="123"),
                mock.Mock(order_id="456")
            ])
        ) == []
        assert sellable_assets
        assert convert_asset_to_target_asset.call_count == len(sellable_assets)
        for call in convert_asset_to_target_asset.mock_calls:
            assert call.kwargs == {"asset_amount": None, "dependencies": signals.get_orders_dependencies([
                mock.Mock(order_id="123"),
                mock.Mock(order_id="456")
            ])}


async def test_convert_asset_to_target_asset(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    trading_mode = _get_trading_mode(exchange_manager)
    sellable_assets = ["USDT", "PLOP"]
    target_asset = "USD"
    tickers = {}
    portfolio = exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
    converter = exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter

    with mock.patch.object(exchange_manager.exchange, "is_market_open_for_order_type", mock.Mock(return_value=True)) \
        as is_market_open_for_order_type_mock:
        # only BTC and USDT in portfolio
        # convert ETH to USDT: nothing to do
        orders = await modes_util.convert_asset_to_target_asset(trading_mode, "ETH", "USDT", tickers)
        assert orders == []
        trading_mode.create_order.assert_not_called()
        is_market_open_for_order_type_mock.assert_not_called()

        # sell BTC
        orders = await modes_util.convert_asset_to_target_asset(trading_mode, "BTC", "USDT", tickers)
        # not working: no BTC pair in exchange_manager.client_symbols (can't create convert order)
        assert orders == []
        trading_mode.create_order.assert_not_called()
        # not called as symbol is not in client_symbols and might not be in symbol_markets
        is_market_open_for_order_type_mock.assert_not_called()

        # add client_symbols pair
        exchange_manager.client_symbols.append("BTC/USDT")

        # not working: no btc price
        assert orders == []
        trading_mode.create_order.assert_not_called()

        # register BTC price
        converter.update_last_price("BTC/USDT", decimal.Decimal(30000))
        orders = await modes_util.convert_asset_to_target_asset(
            trading_mode, "BTC", "USDT", tickers,
            dependencies=signals.get_orders_dependencies([
                mock.Mock(order_id="123"),
                mock.Mock(order_id="456")
            ])
        )
        assert len(orders) == 1
        order = orders[0]
        assert order.order_type == trading_enums.TraderOrderType.SELL_MARKET
        assert order.symbol == "BTC/USDT"
        assert order.origin_quantity == decimal.Decimal(10)
        assert order.created_last_price == decimal.Decimal(30000)
        # market order is instantly filled
        assert order.is_filled()
        assert order.filled_price == order.origin_price
        assert order.filled_quantity > constants.ZERO
        trading_mode.create_order.assert_called_once()
        assert trading_mode.create_order.mock_calls[0].kwargs["dependencies"] == signals.get_orders_dependencies([
            mock.Mock(order_id="123"),
            mock.Mock(order_id="456")
        ])
        trading_mode.create_order.reset_mock()
        is_market_open_for_order_type_mock.assert_called_once_with(
            "BTC/USDT", trading_enums.TraderOrderType.SELL_MARKET
        )
        is_market_open_for_order_type_mock.reset_mock()

    orders = await modes_util.convert_asset_to_target_asset(trading_mode, "USDT", "BTC", tickers)
    assert len(orders) == 1
    order = orders[0]
    assert order.order_type == trading_enums.TraderOrderType.BUY_MARKET
    assert order.symbol == "BTC/USDT"
    assert order.origin_quantity == decimal.Decimal("10.03333333")
    assert order.created_last_price == decimal.Decimal(30000)
    assert order.is_filled()
    trading_mode.create_order.assert_called_once()
    trading_mode.create_order.reset_mock()

    exchange_manager.client_symbols.append("ETH/USDT")
    # using ticker price
    tickers["ETH/USDT"] = {
        trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: decimal.Decimal(1500)
    }

    # reset portfolio
    portfolio["USDT"] = trading_personal_data.SpotAsset("USDT", decimal.Decimal(1000), decimal.Decimal(1000))
    orders = await modes_util.convert_asset_to_target_asset(trading_mode, "USDT", "ETH", tickers)
    assert len(orders) == 1
    order = orders[0]
    assert order.order_type == trading_enums.TraderOrderType.BUY_MARKET
    assert order.symbol == "ETH/USDT"
    assert order.origin_quantity == decimal.Decimal("0.66666666")
    assert order.created_last_price == decimal.Decimal(1500)
    assert order.is_filled()
    trading_mode.create_order.assert_called_once()
    trading_mode.create_order.reset_mock()

    portfolio["ETH"] = trading_personal_data.SpotAsset("ETH", constants.ZERO, constants.ZERO)
    orders = await modes_util.convert_asset_to_target_asset(trading_mode, "ETH", "USDT", tickers)
    # no ETH in portfolio
    assert orders == []
    trading_mode.create_order.assert_not_called()

    portfolio["ETH"] = trading_personal_data.SpotAsset("ETH", constants.ONE, constants.ONE)
    orders = await modes_util.convert_asset_to_target_asset(trading_mode, "ETH", "USDT", tickers)
    assert len(orders) == 1
    order = orders[0]
    assert order.order_type == trading_enums.TraderOrderType.SELL_MARKET
    assert order.symbol == "ETH/USDT"
    assert order.origin_quantity == decimal.Decimal("1")
    assert order.created_last_price == decimal.Decimal(1500)
    assert order.is_filled()
    trading_mode.create_order.assert_called_once()
    trading_mode.create_order.reset_mock()

    # with amount param
    portfolio["ETH"] = trading_personal_data.SpotAsset("ETH", decimal.Decimal("2"), decimal.Decimal("2"))
    orders = await modes_util.convert_asset_to_target_asset(
        trading_mode, "ETH", "USDT", tickers, asset_amount=decimal.Decimal(2)
    )
    assert len(orders) == 1
    order = orders[0]
    assert order.order_type == trading_enums.TraderOrderType.SELL_MARKET
    assert order.symbol == "ETH/USDT"
    assert order.origin_quantity == decimal.Decimal(2)
    assert order.created_last_price == decimal.Decimal(1500)
    assert order.is_filled()
    trading_mode.create_order.assert_called_once()
    trading_mode.create_order.reset_mock()

    orders = await modes_util.convert_asset_to_target_asset(
        trading_mode, "USDT", "ETH", tickers, asset_amount=decimal.Decimal(450)
    )
    assert len(orders) == 1
    order = orders[0]
    assert order.order_type == trading_enums.TraderOrderType.BUY_MARKET
    assert order.symbol == "ETH/USDT"
    assert order.origin_quantity == decimal.Decimal("0.3")
    assert order.created_last_price == decimal.Decimal(1500)
    assert order.is_filled()
    trading_mode.create_order.assert_called_once()
    trading_mode.create_order.reset_mock()

    orders = await modes_util.convert_asset_to_target_asset(
        trading_mode, "USDT", "ETH", tickers, asset_amount=decimal.Decimal(1000)
    )
    assert len(orders) == 1
    order = orders[0]
    assert order.order_type == trading_enums.TraderOrderType.BUY_MARKET
    assert order.symbol == "ETH/USDT"
    assert order.origin_quantity == decimal.Decimal("0.66666666")
    assert order.created_last_price == decimal.Decimal(1500)
    assert order.is_filled()
    trading_mode.create_order.assert_called_once()
    trading_mode.create_order.reset_mock()

    # with fees paid in quote
    fees = {
        trading_enums.FeePropertyColumns.COST.value: "2",
        trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
        trading_enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: True,
    }
    with mock.patch.object(exchange_manager.exchange, "get_trade_fee", mock.Mock(return_value=fees)) \
         as get_trade_fee_mock:
        # cast 1: enough funds in pf to cover fees
        portfolio["USDT"] = trading_personal_data.SpotAsset("USDT", decimal.Decimal(1000), decimal.Decimal(1000))
        orders = await modes_util.convert_asset_to_target_asset(
            trading_mode, "USDT", "ETH", tickers, asset_amount=decimal.Decimal(450)
        )
        assert len(orders) == 1
        order = orders[0]
        assert order.order_type == trading_enums.TraderOrderType.BUY_MARKET
        assert order.symbol == "ETH/USDT"
        assert order.origin_quantity == decimal.Decimal("0.3")
        assert order.created_last_price == decimal.Decimal(1500)
        assert order.is_filled()
        assert get_trade_fee_mock.call_count == 5
        get_trade_fee_mock.reset_mock()
        trading_mode.create_order.assert_called_once()
        trading_mode.create_order.reset_mock()

        # cast 2: reduce amount to cover fees
        portfolio["USDT"] = trading_personal_data.SpotAsset("USDT", decimal.Decimal(1000), decimal.Decimal(1000))
        orders = await modes_util.convert_asset_to_target_asset(
            trading_mode, "USDT", "ETH", tickers, asset_amount=decimal.Decimal(1000)
        )
        assert len(orders) == 1
        order = orders[0]
        assert order.order_type == trading_enums.TraderOrderType.BUY_MARKET
        assert order.symbol == "ETH/USDT"
        assert order.origin_quantity == decimal.Decimal("0.665")   # lower than 0.66666666 when fees is 0 USDT
        assert order.created_last_price == decimal.Decimal(1500)
        assert order.is_filled()
        assert get_trade_fee_mock.call_count == 5
        trading_mode.create_order.assert_called_once()
        trading_mode.create_order.reset_mock()

    # using limit orders
    def _is_market_open_for_order_type(symbol: str, order_type: trading_enums.TraderOrderType):
        return (
            True if order_type in (trading_enums.TraderOrderType.SELL_LIMIT, trading_enums.TraderOrderType.BUY_LIMIT)
            else False
        )

    with mock.patch.object(
        exchange_manager.exchange, "is_market_open_for_order_type",
        mock.Mock(side_effect=_is_market_open_for_order_type)
    ) as is_market_open_for_order_type_mock:
        # cast 1: buying
        portfolio["USDT"] = trading_personal_data.SpotAsset("USDT", decimal.Decimal(1000), decimal.Decimal(1000))
        orders = await modes_util.convert_asset_to_target_asset(
            trading_mode, "USDT", "ETH", tickers, asset_amount=decimal.Decimal(450)
        )
        assert len(orders) == 1
        order = orders[0]
        assert order.order_type == trading_enums.TraderOrderType.BUY_LIMIT
        assert order.symbol == "ETH/USDT"
        # a bit lower than 0.3 because of the price change
        assert order.origin_quantity == decimal.Decimal("0.29850746")
        adapted_price = decimal.Decimal(1500) * (
            constants.ONE + constants.INSTANT_FILLED_LIMIT_ORDER_PRICE_DELTA
        )
        assert order.origin_price == adapted_price
        assert order.created_last_price == adapted_price
        # limit order is designed to be instantly filled, on simulator it should be filled
        assert order.is_filled()
        assert order.filled_price == order.origin_price
        assert order.filled_quantity > constants.ZERO
        assert is_market_open_for_order_type_mock.call_count == 2
        assert is_market_open_for_order_type_mock.mock_calls[0].args == \
               ("ETH/USDT", trading_enums.TraderOrderType.BUY_MARKET)
        assert is_market_open_for_order_type_mock.mock_calls[1].args == \
               ("ETH/USDT", trading_enums.TraderOrderType.BUY_LIMIT)
        is_market_open_for_order_type_mock.reset_mock()
        trading_mode.create_order.assert_called_once()
        trading_mode.create_order.reset_mock()

        # cast 2: selling
        portfolio["USDT"] = trading_personal_data.SpotAsset("USDT", decimal.Decimal(2), decimal.Decimal(2))
        orders = await modes_util.convert_asset_to_target_asset(
            trading_mode, "ETH", "USDT", tickers, asset_amount=decimal.Decimal(2)
        )
        assert len(orders) == 1
        order = orders[0]
        assert order.order_type == trading_enums.TraderOrderType.SELL_LIMIT
        assert order.symbol == "ETH/USDT"
        assert order.origin_quantity == decimal.Decimal("2")
        adapted_price = decimal.Decimal(1500) * (
            constants.ONE - constants.INSTANT_FILLED_LIMIT_ORDER_PRICE_DELTA
        )
        assert order.origin_price == adapted_price
        assert order.created_last_price == adapted_price
        assert order.is_filled()
        assert order.filled_price == order.origin_price
        assert order.filled_quantity > constants.ZERO
        assert is_market_open_for_order_type_mock.call_count == 2
        assert is_market_open_for_order_type_mock.mock_calls[0].args == \
               ("ETH/USDT", trading_enums.TraderOrderType.SELL_MARKET)
        assert is_market_open_for_order_type_mock.mock_calls[1].args == \
               ("ETH/USDT", trading_enums.TraderOrderType.SELL_LIMIT)
        is_market_open_for_order_type_mock.reset_mock()
        trading_mode.create_order.assert_called_once()
        trading_mode.create_order.reset_mock()


async def test_enabled_trader_only(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    
    # Create a mock trading mode class with decorated method
    class TestTradingMode:
        def __init__(self, exchange_manager):
            self.exchange_manager = exchange_manager
            self.logger = mock.Mock()
        
        @modes_util.enabled_trader_only()
        async def default_decorated_method(self, arg1, arg2=None):
            return f"executed with {arg1} and {arg2}"
        
        @modes_util.enabled_trader_only(raise_when_disabled=True)
        async def raise_when_disabled_method(self, arg1):
            return f"executed with {arg1}"
        
        @modes_util.enabled_trader_only(disabled_return_value="custom_return")
        async def custom_return_method(self):
            return "executed"
    
    trading_mode = TestTradingMode(exchange_manager)
    
    # Test 1: Trader enabled - function should execute normally
    trader.set_is_enabled(True)
    result = await trading_mode.default_decorated_method("test", arg2="value")
    assert result == "executed with test and value"
    trading_mode.logger.warning.assert_not_called()
    
    # Test 2: Trader disabled with default decorator - should log warning and return None
    trader.set_is_enabled(False)
    result = await trading_mode.default_decorated_method("test", arg2="value")
    assert result is None
    trading_mode.logger.warning.assert_called_once()
    warning_message = trading_mode.logger.warning.call_args[0][0]
    assert "Trading on" in warning_message
    assert "has been paused" in warning_message
    assert "skipping TestTradingMode execution" in warning_message
    assert exchange_manager.exchange_name in warning_message
    trading_mode.logger.warning.reset_mock()
    
    # Test 3: Trader disabled with raise_when_disabled=True - should raise TraderDisabledError
    trader.set_is_enabled(False)
    with pytest.raises(errors.TraderDisabledError, match="has been paused"):
        await trading_mode.raise_when_disabled_method("test")
    trading_mode.logger.warning.assert_not_called()
    
    # Test 4: Trader disabled with custom disabled_return_value - should return custom value
    trader.set_is_enabled(False)
    result = await trading_mode.custom_return_method()
    assert result == "custom_return"
    trading_mode.logger.warning.assert_called_once()
    trading_mode.logger.warning.reset_mock()
    
    # Test 5: Trader enabled with custom_return_method - should execute normally
    trader.set_is_enabled(True)
    result = await trading_mode.custom_return_method()
    assert result == "executed"
    trading_mode.logger.warning.assert_not_called()


def _get_trading_mode(exchange_manager):
    async def _create_order(order, dependencies=None):
        return await signals.create_order(
            exchange_manager, False, order, dependencies=dependencies
        )

    return mock.Mock(
        exchange_manager=exchange_manager,
        create_order=mock.AsyncMock(side_effect=_create_order)
    )


