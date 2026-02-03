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
import pytest
import mock
import decimal

import octobot_trading.personal_data as trading_personal_data
import octobot_trading.enums as trading_enums
import octobot_trading.modes.script_keywords as script_keywords
import octobot_trading.modes.script_keywords.basic_keywords.account_balance as account_balance
import octobot_trading.constants as trading_constants
import octobot_commons.constants as commons_constants

from tests import event_loop
from tests.modes.script_keywords import null_context, mock_context
from tests.exchanges import \
    backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_total_account_balance(mock_context):
    mock_context.exchange_manager.exchange_personal_data. \
        portfolio_manager.portfolio_value_holder.portfolio_current_value = decimal.Decimal(999)
    mock_context.exchange_manager.exchange_personal_data.portfolio_manager.reference_market = "USDT"
    with mock.patch.object(trading_personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=100)) \
            as get_up_to_date_price:
        assert await script_keywords.total_account_balance(mock_context) == decimal.Decimal("9.99")
        get_up_to_date_price.assert_called_once_with(mock_context.exchange_manager, symbol=mock_context.symbol,
                                                     timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT)


async def test_available_account_balance(mock_context):
    current_symbol_holding = decimal.Decimal("100")
    market_quantity = decimal.Decimal("50")

    async def _get_pre_order_data(
        exchange_manager, symbol: str, timeout: int = None,
        portfolio_type=commons_constants.PORTFOLIO_AVAILABLE,
        target_price=None
    ):
        if portfolio_type == commons_constants.PORTFOLIO_AVAILABLE:
            return current_symbol_holding, "current_market_holding", market_quantity, "current_price", "symbol_market"
        return current_symbol_holding*2, "current_market_holding", market_quantity*2, "current_price", "symbol_market"

    with mock.patch.object(trading_personal_data, "get_pre_order_data", mock.AsyncMock(side_effect=_get_pre_order_data)) \
            as get_pre_order_data_mock, \
            mock.patch.object(account_balance, "_get_locked_amount_in_stop_orders",
                              mock.Mock(return_value=trading_constants.ONE)) as _get_locked_amount_in_stop_orders_mock:
        assert market_quantity == await script_keywords.available_account_balance(
            mock_context, side=trading_enums.TradeOrderSide.BUY.value, use_total_holding=False, is_stop_order=False,
            target_price=trading_constants.ZERO
        )
        get_pre_order_data_mock.assert_called_once_with(mock_context.exchange_manager, symbol=mock_context.symbol,
                                                        timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
                                                        portfolio_type=commons_constants.PORTFOLIO_AVAILABLE,
                                                        target_price=trading_constants.ZERO)
        get_pre_order_data_mock.reset_mock()
        _get_locked_amount_in_stop_orders_mock.assert_not_called()
        assert current_symbol_holding * 2 == await script_keywords.available_account_balance(
            mock_context, side=trading_enums.TradeOrderSide.SELL.value, use_total_holding=True)
        get_pre_order_data_mock.assert_called_once_with(mock_context.exchange_manager, symbol=mock_context.symbol,
                                                        timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
                                                        portfolio_type=commons_constants.PORTFOLIO_TOTAL,
                                                        target_price=None)
        get_pre_order_data_mock.reset_mock()
        _get_locked_amount_in_stop_orders_mock.assert_not_called()
        assert current_symbol_holding * 2 - trading_constants.ONE == await script_keywords.available_account_balance(
            mock_context, side=trading_enums.TradeOrderSide.SELL.value, use_total_holding=True, is_stop_order=True)
        get_pre_order_data_mock.assert_called_once_with(mock_context.exchange_manager, symbol=mock_context.symbol,
                                                        timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
                                                        portfolio_type=commons_constants.PORTFOLIO_TOTAL,
                                                        target_price=None)
        _get_locked_amount_in_stop_orders_mock.assert_called_once_with(mock_context,
                                                                       trading_enums.TradeOrderSide.SELL.value)
        get_pre_order_data_mock.reset_mock()
        _get_locked_amount_in_stop_orders_mock.reset_mock()
        assert market_quantity * 2 - trading_constants.ONE == await script_keywords.available_account_balance(
            mock_context, side=trading_enums.TradeOrderSide.BUY.value, use_total_holding=True, is_stop_order=True)
        get_pre_order_data_mock.assert_called_once_with(mock_context.exchange_manager, symbol=mock_context.symbol,
                                                        timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
                                                        portfolio_type=commons_constants.PORTFOLIO_TOTAL,
                                                        target_price=None)
        _get_locked_amount_in_stop_orders_mock.assert_called_once_with(mock_context,
                                                                       trading_enums.TradeOrderSide.BUY.value)
        get_pre_order_data_mock.reset_mock()
        _get_locked_amount_in_stop_orders_mock.reset_mock()

        buy_1 = trading_personal_data.BuyLimitOrder(mock_context.trader)
        buy_1.origin_quantity = decimal.Decimal("10")
        buy_1.origin_price = decimal.Decimal("100")
        buy_2 = trading_personal_data.BuyLimitOrder(mock_context.trader)
        buy_2.origin_quantity = decimal.Decimal("3")
        buy_2.origin_price = decimal.Decimal("40")
        sell_1 = trading_personal_data.SellLimitOrder(mock_context.trader)
        sell_1.origin_quantity = decimal.Decimal("2.21")
        sell_1.origin_price = decimal.Decimal("200")
        assert market_quantity + buy_1.origin_quantity + buy_2.origin_quantity == \
           await script_keywords.available_account_balance(
                mock_context, side=trading_enums.TradeOrderSide.BUY.value, use_total_holding=False, is_stop_order=False,
                orders_to_be_ignored=[buy_1, buy_2, sell_1]
            )
        assert get_pre_order_data_mock.call_count == 2
        _get_locked_amount_in_stop_orders_mock.assert_not_called()
        get_pre_order_data_mock.reset_mock()
        _get_locked_amount_in_stop_orders_mock.reset_mock()


async def test_adapt_amount_to_holdings(null_context):
    with mock.patch.object(account_balance, "available_account_balance",
                           mock.AsyncMock(return_value=decimal.Decimal(1))) as available_account_balance_mock:
        assert await script_keywords.adapt_amount_to_holdings(null_context,
                                                              decimal.Decimal(0),
                                                              trading_enums.TradeOrderSide.SELL,
                                                              False,
                                                              "reduce_only",
                                                              "is_stop_order",
                                                              target_price=trading_constants.ONE_HUNDRED
                                                              ) == decimal.Decimal(0)
        available_account_balance_mock.assert_called_once_with(null_context, trading_enums.TradeOrderSide.SELL,
                                                               use_total_holding=False, is_stop_order="is_stop_order",
                                                               reduce_only="reduce_only",
                                                               target_price=trading_constants.ONE_HUNDRED,
                                                               orders_to_be_ignored=None)
        available_account_balance_mock.reset_mock()
        assert await script_keywords.adapt_amount_to_holdings(null_context,
                                                              decimal.Decimal(1),
                                                              trading_enums.TradeOrderSide.SELL,
                                                              True,
                                                              "reduce_only",
                                                              "is_stop_order",
                                                              orders_to_be_ignored=["plop"]) == decimal.Decimal(1)
        available_account_balance_mock.assert_called_once_with(null_context, trading_enums.TradeOrderSide.SELL,
                                                               use_total_holding=True, is_stop_order="is_stop_order",
                                                               reduce_only="reduce_only",
                                                               target_price=None,
                                                               orders_to_be_ignored=["plop"])
        assert await script_keywords.adapt_amount_to_holdings(null_context,
                                                              decimal.Decimal(2),
                                                              trading_enums.TradeOrderSide.SELL,
                                                              False,
                                                              "reduce_only",
                                                              "is_stop_order") == decimal.Decimal(1)


async def test_get_locked_amount_in_stop_orders(mock_context):
    mock_context.exchange_manager = mock.Mock()
    mock_context.exchange_manager.exchange_personal_data = mock.Mock()
    mock_context.exchange_manager.exchange_personal_data.orders_manager = mock.Mock()

    mock_context.exchange_manager.exchange_personal_data.orders_manager.get_open_orders = mock.Mock(return_value=[])
    assert account_balance._get_locked_amount_in_stop_orders(mock_context, "buy") == trading_constants.ZERO

    order = trading_personal_data.StopLossOrder(mock_context.trader)
    order.side = trading_enums.TradeOrderSide.SELL
    order.origin_quantity = decimal.Decimal("10")

    mock_context.exchange_manager.exchange_personal_data.orders_manager.get_open_orders = \
        mock.Mock(return_value=[order])
    assert account_balance._get_locked_amount_in_stop_orders(mock_context, "buy") == trading_constants.ZERO

    mock_context.exchange_manager.exchange_personal_data.orders_manager.get_open_orders = \
        mock.Mock(return_value=[order])
    assert account_balance._get_locked_amount_in_stop_orders(mock_context, "sell") == decimal.Decimal("10")

    order_2 = trading_personal_data.StopLossLimitOrder(mock_context.trader)
    order_2.side = trading_enums.TradeOrderSide.SELL
    order_2.origin_quantity = decimal.Decimal("20")

    order_3 = trading_personal_data.StopLossLimitOrder(mock_context.trader)
    order_3.side = trading_enums.TradeOrderSide.BUY
    order_3.origin_quantity = decimal.Decimal("50")

    order_4 = trading_personal_data.BuyLimitOrder(mock_context.trader)
    order_4.side = trading_enums.TradeOrderSide.SELL
    order_4.origin_quantity = decimal.Decimal("100")

    mock_context.exchange_manager.exchange_personal_data.orders_manager.get_open_orders = \
        mock.Mock(return_value=[order, order_2, order_3, order_4])
    assert account_balance._get_locked_amount_in_stop_orders(mock_context, "sell") == decimal.Decimal("30")
