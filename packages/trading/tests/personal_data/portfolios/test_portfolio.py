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
import copy
import os
import decimal

import mock
import pytest
import octobot_commons.constants as commons_constants

import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.enums as enums
from octobot_trading.enums import TraderOrderType, TradeOrderSide
from octobot_trading.personal_data.orders import BuyLimitOrder
from octobot_trading.personal_data.orders import SellLimitOrder
from octobot_trading.personal_data.orders import StopLossOrder
from octobot_trading.personal_data.orders import BuyMarketOrder
from octobot_trading.personal_data.orders.types.market.sell_market_order import SellMarketOrder
import octobot_trading.personal_data.orders.groups as order_groups
from tests.test_utils.order_util import fill_market_order, fill_limit_or_stop_order

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_load_portfolio(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    assert portfolio_manager.portfolio.portfolio['BTC'].available == decimal.Decimal('10')
    assert portfolio_manager.portfolio.portfolio['BTC'].total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.portfolio['USDT'].available == decimal.Decimal('1000')
    assert portfolio_manager.portfolio.portfolio['USDT'].total == decimal.Decimal('1000')


async def test_copy_portfolio(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    pf1 = portfolio_manager.portfolio
    pf2 = copy.copy(pf1)
    pf1.portfolio['BTC'].available = decimal.Decimal('5')
    pf1.portfolio['BTC'].total = decimal.Decimal('9')
    pf1.portfolio['USDT'].available = decimal.Decimal('10.5')
    pf1.portfolio['USDT'].total = decimal.Decimal('1.3')
    assert pf1.portfolio['BTC'].available != pf2.portfolio['BTC'].available
    assert pf1.portfolio['BTC'].total != pf2.portfolio['BTC'].total
    assert pf1.portfolio['USDT'].available != pf2.portfolio['USDT'].available
    assert pf1.portfolio['USDT'].total != pf2.portfolio['USDT'].total
    assert pf1 != pf2


async def test_get_portfolio_from_amount_dict(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    assert portfolio_manager.portfolio.get_portfolio_from_amount_dict(
        {"zyx": {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('10'),
                 commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('24')},
         "BTC": {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('0.1'),
                 commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('0.1')}}) == {
               'zyx': {'available': decimal.Decimal('10'), 'total': decimal.Decimal('24')},
               'BTC': {'available': decimal.Decimal('0.1'), 'total': decimal.Decimal('0.1')}
           }
    assert portfolio_manager.portfolio.get_portfolio_from_amount_dict({}) == {}
    with pytest.raises(RuntimeError):
        portfolio_manager.portfolio.get_portfolio_from_amount_dict({
            "zyx":  {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('10'),
                     commons_constants.PORTFOLIO_TOTAL: '24'},
            "BTC":  {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('10'),
                     commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('24')},
        })
    with pytest.raises(RuntimeError):
        portfolio_manager.portfolio.get_portfolio_from_amount_dict({
            "zyx":  {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('10'),
                     commons_constants.PORTFOLIO_TOTAL: 24},
            "BTC":  {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('10'),
                     commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('24')},
        })
    with pytest.raises(AttributeError):
        portfolio_manager.portfolio.get_portfolio_from_amount_dict({"BTC":  '10'})


async def test_get_currency_portfolio(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("DOT").total == decimal.Decimal('0')


async def test_update_portfolio_from_balance(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    test_portfolio = {"zyx": {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('0.1'),
                              commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('0.1')},
                      "BTC": {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('1'),
                              commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('1')},
                      "ETH": {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('50'),
                              commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('150')}}

    assert portfolio_manager.portfolio.update_portfolio_from_balance(test_portfolio)
    assert portfolio_manager.portfolio.portfolio['BTC'].available == decimal.Decimal('1')
    assert portfolio_manager.portfolio.portfolio['BTC'].total == decimal.Decimal('1')
    assert portfolio_manager.portfolio.portfolio['zyx'].available == decimal.Decimal('0.1')
    assert portfolio_manager.portfolio.portfolio['zyx'].total == decimal.Decimal('0.1')
    assert portfolio_manager.portfolio.portfolio['ETH'].available == decimal.Decimal('50')
    assert portfolio_manager.portfolio.portfolio['ETH'].total == decimal.Decimal('150')

    # should return False when no update made
    assert not portfolio_manager.portfolio.update_portfolio_from_balance(test_portfolio, force_replace=False)


async def test_update_portfolio_from_balance_with_deltas(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    test_portfolio = {"BTC": {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('1'),
                              commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('1')}}

    assert portfolio_manager.portfolio.update_portfolio_from_balance(test_portfolio, force_replace=False)
    assert portfolio_manager.portfolio.portfolio['BTC'].available == decimal.Decimal('1')
    assert portfolio_manager.portfolio.portfolio['BTC'].total == decimal.Decimal('1')
    assert portfolio_manager.portfolio.portfolio['USDT'].available == decimal.Decimal('1000')
    assert portfolio_manager.portfolio.portfolio['USDT'].total == decimal.Decimal('1000')

    test_portfolio_2 = {"DOT": {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('1'),
                                 commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('2')}}

    assert portfolio_manager.portfolio.update_portfolio_from_balance(test_portfolio_2, force_replace=False)
    assert portfolio_manager.portfolio.portfolio['BTC'].available == decimal.Decimal('1')
    assert portfolio_manager.portfolio.portfolio['BTC'].total == decimal.Decimal('1')
    assert portfolio_manager.portfolio.portfolio['USDT'].available == decimal.Decimal('1000')
    assert portfolio_manager.portfolio.portfolio['USDT'].total == decimal.Decimal('1000')
    assert portfolio_manager.portfolio.portfolio['DOT'].available == decimal.Decimal('1')
    assert portfolio_manager.portfolio.portfolio['DOT'].total == decimal.Decimal('2')

    test_portfolio_3 = {"USDT": {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('250'),
                                 commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('500')}}

    assert portfolio_manager.portfolio.update_portfolio_from_balance(test_portfolio_3, force_replace=False)
    assert portfolio_manager.portfolio.portfolio['BTC'].available == decimal.Decimal('1')
    assert portfolio_manager.portfolio.portfolio['BTC'].total == decimal.Decimal('1')
    assert portfolio_manager.portfolio.portfolio['USDT'].available == decimal.Decimal('250')
    assert portfolio_manager.portfolio.portfolio['USDT'].total == decimal.Decimal('500')
    assert portfolio_manager.portfolio.portfolio['DOT'].available == decimal.Decimal('1')
    assert portfolio_manager.portfolio.portfolio['DOT'].total == decimal.Decimal('2')

    test_portfolio_4 = {"USDT": {commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal('100'),
                                 commons_constants.PORTFOLIO_TOTAL: decimal.Decimal('100')}}

    assert portfolio_manager.portfolio.update_portfolio_from_balance(test_portfolio_4, force_replace=True)
    assert portfolio_manager.portfolio.portfolio['USDT'].available == decimal.Decimal('100')
    assert portfolio_manager.portfolio.portfolio['USDT'].total == decimal.Decimal('100')


async def test_update_portfolio(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    # Test buy order
    limit_buy = BuyLimitOrder(trader)
    limit_buy.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="BTC/USDT",
                     current_price=70,
                     quantity=10,
                     price=70)

    # update portfolio with creations
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('300')

    await fill_limit_or_stop_order(limit_buy)

    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('20')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('300')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('20')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('300')

    # Test buy order
    market_sell = SellMarketOrder(trader)
    market_sell.update(order_type=TraderOrderType.SELL_MARKET,
                       symbol="BTC/USDT",
                       current_price=80,
                       quantity=8,
                       price=80)

    # update portfolio with creations
    portfolio_manager.portfolio.update_portfolio_available(market_sell, True)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('12')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('300')

    await fill_market_order(market_sell)

    # when filling market sell
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('12')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('940')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('12')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('940')


async def test_update_portfolio_with_filled_orders(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    # force fees => should have consequences
    exchange_manager.exchange.config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_SIMULATOR_FEES] = {
        commons_constants.CONFIG_SIMULATOR_FEES_MAKER: 0.05,
        commons_constants.CONFIG_SIMULATOR_FEES_TAKER: 0.1
    }

    # Test buy order
    market_sell = SellMarketOrder(trader)
    market_sell.update(order_type=TraderOrderType.SELL_MARKET,
                       symbol="BTC/USDT",
                       current_price=decimal.Decimal(str(70)),
                       quantity=decimal.Decimal(str(3)),
                       price=decimal.Decimal(str(70)))

    # Test sell order
    limit_sell = SellLimitOrder(trader)
    limit_sell.update(order_type=TraderOrderType.SELL_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal(str(100)),
                      quantity=decimal.Decimal(str(4.2)),
                      price=decimal.Decimal(str(100)))

    # Test stop loss order
    stop_loss = StopLossOrder(trader)
    stop_loss.update(order_type=TraderOrderType.STOP_LOSS,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal(str(80)),
                     quantity=decimal.Decimal(str(4.2)),
                     price=decimal.Decimal(str(80)))

    oco_group = exchange_manager.exchange_personal_data.orders_manager\
        .create_group(order_groups.OneCancelsTheOtherOrderGroup)
    limit_sell.add_to_order_group(oco_group)
    stop_loss.add_to_order_group(oco_group)

    # Test buy order
    limit_buy = BuyLimitOrder(trader)
    limit_buy.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal(str(51)),
                     quantity=decimal.Decimal(str(2)),
                     price=decimal.Decimal(str(50)))
    limit_buy_2 = BuyLimitOrder(trader)
    limit_buy_2.update(order_type=TraderOrderType.BUY_LIMIT,
                       symbol="BTC/USDT",
                       current_price=decimal.Decimal(str(51)),
                       quantity=decimal.Decimal(str(2)),
                       price=decimal.Decimal(str(50)))

    # update portfolio with creations
    portfolio_manager.portfolio.update_portfolio_available(market_sell, True)
    portfolio_manager.portfolio.update_portfolio_available(stop_loss, True)
    # simulate fees in USDT (ex: Kucoin, OKX)
    with mock.patch.object(limit_buy.exchange_manager.exchange.connector, "_get_fees_currency", return_value="USDT") \
         as _get_fees_currency_mock:
        # taker fees are locked
        portfolio_manager.portfolio.update_portfolio_available(limit_sell, True)
        portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_buy_2, True)

    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('2.8')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('799.9')

    # when cancelling limit sell, market sell and stop orders
    portfolio_manager.portfolio.update_portfolio_available(stop_loss, False)
    # simulate fees in USDT (ex: Kucoin, OKX)
    with mock.patch.object(limit_buy.exchange_manager.exchange.connector, "_get_fees_currency", return_value="USDT") \
         as _get_fees_currency_mock:
        portfolio_manager.portfolio.update_portfolio_available(limit_sell, False)

    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('7')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('799.9')

    # when filling limit buy
    # simulate fees in USDT (ex: Kucoin, OKX)
    with mock.patch.object(limit_buy.exchange_manager.exchange.connector, "_get_fees_currency", return_value="USDT") \
         as _get_fees_currency_mock:
        await fill_limit_or_stop_order(limit_buy)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('9')
    # USDT available is now 899.95 as maker fees are applied
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('799.95')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('12')
    # USDT total is now 899.95 as maker fees are applied
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('899.95')

    # when filling market sell
    await fill_market_order(market_sell)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('9')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1009.74')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('9')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1109.74')

    # when filling limit buy 2 (fees paid in BTC)
    await fill_market_order(limit_buy_2)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10.999')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1009.74')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10.999')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1009.74')


async def test_update_portfolio_with_cancelled_orders(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    # force fees => shouldn't do anything
    exchange_manager.exchange.config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_SIMULATOR_FEES] = {
        commons_constants.CONFIG_SIMULATOR_FEES_MAKER: decimal.Decimal('0.05'),
        commons_constants.CONFIG_SIMULATOR_FEES_TAKER: decimal.Decimal('0.1')
    }

    # Test buy order
    market_sell = SellMarketOrder(trader)
    market_sell.update(order_type=TraderOrderType.SELL_MARKET,
                       symbol="BTC/USDT",
                       current_price=decimal.Decimal(str(80)),
                       quantity=decimal.Decimal(str(4.1)),
                       price=decimal.Decimal(str(80)))

    # Test sell order
    limit_sell = SellLimitOrder(trader)
    limit_sell.update(order_type=TraderOrderType.SELL_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal(str(10)),
                      quantity=decimal.Decimal(str(4.2)),
                      price=decimal.Decimal(str(10)))

    # Test stop loss order
    stop_loss = StopLossOrder(trader)
    stop_loss.update(order_type=TraderOrderType.STOP_LOSS,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal(str(80)),
                     quantity=decimal.Decimal(str(3.6)),
                     price=decimal.Decimal(str(80)))

    portfolio_manager.portfolio.update_portfolio_available(stop_loss, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, True)
    assert round(portfolio_manager.portfolio.get_currency_portfolio("BTC").available,
                 1) == decimal.Decimal('5.8')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')

    # Test buy order
    limit_buy = BuyLimitOrder(trader)
    limit_buy.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal(str(50)),
                     quantity=decimal.Decimal(str(4)),
                     price=decimal.Decimal(str(50)))

    # simulate fees in USDT (ex: Kucoin, OKX)
    with mock.patch.object(limit_buy.exchange_manager.exchange.connector, "_get_fees_currency", return_value="USDT") \
         as _get_fees_currency_mock:
        portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)
    assert round(portfolio_manager.portfolio.get_currency_portfolio("BTC").available,
                 1) == decimal.Decimal('5.8')
    # also locked 0.2 USDT for fees (use taker fees to be sure to have enough funds if order is filled as taker)
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('799.8')

    portfolio_manager.portfolio.update_portfolio_available(market_sell, True)

    assert round(portfolio_manager.portfolio.get_currency_portfolio("BTC").available,
                 1) == decimal.Decimal('1.7')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal(
        '799.8')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal(
        '10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal(
        '1000')

    # with no filled orders
    portfolio_manager.portfolio.update_portfolio_available(stop_loss, False)
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, False)
    with mock.patch.object(limit_buy.exchange_manager.exchange.connector, "_get_fees_currency", return_value="USDT") \
         as _get_fees_currency_mock:
        portfolio_manager.portfolio.update_portfolio_available(limit_buy, False)
    portfolio_manager.portfolio.update_portfolio_available(market_sell, False)

    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal(
        '10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal(
        '1000')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal(
        '10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal(
        '1000')


async def test_update_portfolio_with_stop_loss_sell_orders(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    # Test buy order
    limit_sell = SellLimitOrder(trader)
    limit_sell.update(order_type=TraderOrderType.SELL_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal(str(90)),
                      quantity=decimal.Decimal(str(4)),
                      price=decimal.Decimal(str(90)))

    # Test buy order
    limit_buy = BuyLimitOrder(trader)
    limit_buy.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal(str(50)),
                     quantity=decimal.Decimal(str(4)),
                     price=decimal.Decimal(str(50)))

    # Test stop loss order
    stop_loss = StopLossOrder(trader, side=TradeOrderSide.SELL)
    stop_loss.update(order_type=TraderOrderType.STOP_LOSS,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal(str(60)),
                     quantity=decimal.Decimal(str(4)),
                     price=decimal.Decimal(str(60)))

    portfolio_manager.portfolio.update_portfolio_available(stop_loss, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)

    assert round(portfolio_manager.portfolio.get_currency_portfolio("BTC").available, 1) == decimal.Decimal('6')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('800')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # cancel limits
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, False)
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, False)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    await fill_limit_or_stop_order(stop_loss)

    # filling stop loss
    # typical stop loss behavior --> update available before update portfolio
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('6')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1240')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('6')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1240')


async def test_update_portfolio_with_stop_loss_buy_orders(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    # Test buy order
    limit_sell = SellLimitOrder(trader)
    limit_sell.update(order_type=TraderOrderType.SELL_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal(str(90)),
                      quantity=decimal.Decimal(str(4)),
                      price=decimal.Decimal(str(90)))

    # Test buy order
    limit_buy = BuyLimitOrder(trader)
    limit_buy.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal(str(50)),
                     quantity=decimal.Decimal(str(4)),
                     price=decimal.Decimal(str(50)))

    # Test stop loss order
    stop_loss = StopLossOrder(trader, side=TradeOrderSide.BUY)
    stop_loss.update(order_type=TraderOrderType.STOP_LOSS,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal(str(60)),
                     quantity=decimal.Decimal(str(4)),
                     price=decimal.Decimal(str(60)))

    portfolio_manager.portfolio.update_portfolio_available(stop_loss, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)

    assert round(portfolio_manager.portfolio.get_currency_portfolio("BTC").available, 1) == decimal.Decimal('6')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('800')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # cancel limits
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, False)
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, False)

    await fill_limit_or_stop_order(stop_loss)

    # filling stop loss
    # typical stop loss behavior --> update available before update portfolio
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('14')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('760')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('14')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('760')


async def test_update_portfolio_with_some_filled_orders(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    # Test buy order
    limit_sell = SellLimitOrder(trader)
    limit_sell.update(order_type=TraderOrderType.SELL_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal(str(90)),
                      quantity=decimal.Decimal(str(4)),
                      price=decimal.Decimal(str(90)))

    # Test buy order
    limit_buy = BuyLimitOrder(trader)
    limit_buy.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal(str(60)),
                     quantity=decimal.Decimal(str(2)),
                     price=decimal.Decimal(str(60)))

    # Test buy order
    limit_buy_2 = BuyLimitOrder(trader)
    limit_buy_2.update(order_type=TraderOrderType.BUY_LIMIT,
                       symbol="BTC/USDT",
                       current_price=decimal.Decimal(str(50)),
                       quantity=decimal.Decimal(str(4)),
                       price=decimal.Decimal(str(50)))

    # Test sell order
    limit_sell_2 = SellLimitOrder(trader)
    limit_sell_2.update(order_type=TraderOrderType.SELL_LIMIT,
                        symbol="BTC/USDT",
                        current_price=decimal.Decimal(str(10)),
                        quantity=decimal.Decimal(str(2)),
                        price=decimal.Decimal(str(10)))

    # Test stop loss order
    stop_loss_2 = StopLossOrder(trader)
    stop_loss_2.update(order_type=TraderOrderType.STOP_LOSS,
                       symbol="BTC/USDT",
                       current_price=decimal.Decimal(str(10)),
                       quantity=decimal.Decimal(str(2)),
                       price=decimal.Decimal(str(10)))

    # Test sell order
    limit_sell_3 = SellLimitOrder(trader)
    limit_sell_3.update(order_type=TraderOrderType.SELL_LIMIT,
                        symbol="BTC/USDT",
                        current_price=decimal.Decimal(str(20)),
                        quantity=decimal.Decimal(str(1)),
                        price=decimal.Decimal(str(20)))

    # Test stop loss order
    stop_loss_3 = StopLossOrder(trader)
    stop_loss_3.update(order_type=TraderOrderType.STOP_LOSS,
                       symbol="BTC/USDT",
                       current_price=decimal.Decimal(str(20)),
                       quantity=decimal.Decimal(str(1)),
                       price=decimal.Decimal(str(20)))

    portfolio_manager.portfolio.update_portfolio_available(stop_loss_2, True)
    portfolio_manager.portfolio.update_portfolio_available(stop_loss_3, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_sell_2, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_sell_3, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)
    portfolio_manager.portfolio.update_portfolio_available(limit_buy_2, True)

    assert round(portfolio_manager.portfolio.get_currency_portfolio("BTC").available,
                 1) == 3
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal(
        '680')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal(
        '10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal(
        '1000')

    # Test stop loss order
    stop_loss_4 = StopLossOrder(trader, side=TradeOrderSide.BUY)
    stop_loss_4.update(order_type=TraderOrderType.STOP_LOSS,
                       symbol="BTC/USDT",
                       current_price=decimal.Decimal(str(20)),
                       quantity=decimal.Decimal(str(4)),
                       price=decimal.Decimal(str(20)))

    # Test stop loss order
    stop_loss_5 = StopLossOrder(trader, side=TradeOrderSide.BUY)
    stop_loss_5.update(order_type=TraderOrderType.STOP_LOSS,
                       symbol="BTC/USDT",
                       current_price=decimal.Decimal(str(200)),
                       quantity=decimal.Decimal(str(4)),
                       price=decimal.Decimal(str(20)))
    portfolio_manager.portfolio.update_portfolio_available(stop_loss_5, True)

    # portfolio did not change as stop losses are not affecting available funds
    assert round(portfolio_manager.portfolio.get_currency_portfolio("BTC").available,
                 1) == 3
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal(
        '680')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal(
        '10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal(
        '1000')

    # cancels
    portfolio_manager.portfolio.update_portfolio_available(stop_loss_3, False)
    portfolio_manager.portfolio.update_portfolio_available(stop_loss_5, False)
    portfolio_manager.portfolio.update_portfolio_available(limit_sell_2, False)
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, False)

    # filling
    await fill_limit_or_stop_order(stop_loss_2)
    await fill_limit_or_stop_order(limit_sell)
    await fill_limit_or_stop_order(limit_sell_3)
    await fill_limit_or_stop_order(limit_buy_2)

    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal(
        '7')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal(
        '1200')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('7')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal(
        '1200')

    await fill_limit_or_stop_order(stop_loss_4)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal(
        '11')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal(
        '1120')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal(
        '11')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal(
        '1120')


async def test_update_portfolio_with_multiple_filled_orders(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    fees = {
        enums.ExchangeConstantsMarketPropertyColumns.TAKER.value: 0.001,
        enums.ExchangeConstantsMarketPropertyColumns.MAKER.value: 0.001,
        enums.ExchangeConstantsMarketPropertyColumns.FEE.value: 0.001
    }

    with mock.patch.object(exchange_manager.exchange.connector, "get_fees", return_value=fees) \
         as get_fees_mock:
        # Test buy order
        limit_sell = SellLimitOrder(trader)
        limit_sell.update(order_type=TraderOrderType.SELL_LIMIT,
                          symbol="BTC/USDT",
                          current_price=decimal.Decimal(str(90)),
                          quantity=decimal.Decimal(str(4)),
                          price=decimal.Decimal(str(90)))

        # Test buy order
        limit_buy = BuyLimitOrder(trader)
        limit_buy.update(order_type=TraderOrderType.BUY_LIMIT,
                         symbol="BTC/USDT",
                         current_price=decimal.Decimal(str(60)),
                         quantity=decimal.Decimal(str(2)),
                         price=decimal.Decimal(str(60)))

        # Test buy order
        limit_buy_2 = BuyLimitOrder(trader)
        limit_buy_2.update(order_type=TraderOrderType.BUY_LIMIT,
                           symbol="BTC/USDT",
                           current_price=decimal.Decimal(str(50)),
                           quantity=decimal.Decimal(str(4)),
                           price=decimal.Decimal(str(50)))

        # Test buy order
        limit_buy_3 = BuyLimitOrder(trader)
        limit_buy_3.update(order_type=TraderOrderType.BUY_LIMIT,
                           symbol="BTC/USDT",
                           current_price=decimal.Decimal(str(46)),
                           quantity=decimal.Decimal(str(2)),
                           price=decimal.Decimal(str(46)))

        # Test buy order
        limit_buy_4 = BuyLimitOrder(trader)
        limit_buy_4.update(order_type=TraderOrderType.BUY_LIMIT,
                           symbol="BTC/USDT",
                           current_price=decimal.Decimal(str(41)),
                           quantity=decimal.Decimal(str(1.78)),
                           price=decimal.Decimal(str(41)))

        # Test buy order
        limit_buy_5 = BuyLimitOrder(trader)
        limit_buy_5.update(order_type=TraderOrderType.BUY_LIMIT,
                           symbol="BTC/USDT",
                           current_price=decimal.Decimal(str(0.2122427)),
                           quantity=decimal.Decimal(str(3.72448)),
                           price=decimal.Decimal(str(0.2122427)))

        # Test buy order
        limit_buy_6 = BuyLimitOrder(trader)
        limit_buy_6.update(order_type=TraderOrderType.BUY_LIMIT,
                           symbol="BTC/USDT",
                           current_price=decimal.Decimal(str(430)),
                           quantity=decimal.Decimal(str(1.05)),
                           price=decimal.Decimal(str(430)))

        # Test sell order
        limit_sell_2 = SellLimitOrder(trader)
        limit_sell_2.update(order_type=TraderOrderType.SELL_LIMIT,
                            symbol="BTC/USDT",
                            current_price=decimal.Decimal(str(10)),
                            quantity=decimal.Decimal(str(2)),
                            price=decimal.Decimal(str(10)))

        # Test stop loss order
        stop_loss_2 = StopLossOrder(trader)
        stop_loss_2.update(order_type=TraderOrderType.STOP_LOSS,
                           symbol="BTC/USDT",
                           current_price=decimal.Decimal(str(10)),
                           quantity=decimal.Decimal(str(2)),
                           price=decimal.Decimal(str(10)))

        # Test sell order
        limit_sell_3 = SellLimitOrder(trader)
        limit_sell_3.update(order_type=TraderOrderType.SELL_LIMIT,
                            symbol="BTC/USDT",
                            current_price=decimal.Decimal(str(20)),
                            quantity=decimal.Decimal(str(1)),
                            price=decimal.Decimal(str(20)))

        # Test stop loss order
        stop_loss_3 = StopLossOrder(trader)
        stop_loss_3.update(order_type=TraderOrderType.STOP_LOSS,
                           symbol="BTC/USDT",
                           current_price=decimal.Decimal(str(20)),
                           quantity=decimal.Decimal(str(1)),
                           price=decimal.Decimal(str(20)))

        # Test sell order
        limit_sell_4 = SellLimitOrder(trader)
        limit_sell_4.update(order_type=TraderOrderType.SELL_LIMIT,
                            symbol="BTC/USDT",
                            current_price=decimal.Decimal(str(50)),
                            quantity=decimal.Decimal(str(0.2)),
                            price=decimal.Decimal(str(50)))

        # Test stop loss order
        stop_loss_4 = StopLossOrder(trader, side=TradeOrderSide.BUY)
        stop_loss_4.update(order_type=TraderOrderType.STOP_LOSS,
                           symbol="BTC/USDT",
                           current_price=decimal.Decimal(str(45)),
                           quantity=decimal.Decimal(str(0.2)),
                           price=decimal.Decimal(str(45)))

        # Test sell order
        limit_sell_5 = SellLimitOrder(trader)
        limit_sell_5.update(order_type=TraderOrderType.SELL_LIMIT,
                            symbol="BTC/USDT",
                            current_price=decimal.Decimal(str(11)),
                            quantity=decimal.Decimal(str(0.7)),
                            price=decimal.Decimal(str(11)))

        # Test stop loss order
        stop_loss_5 = StopLossOrder(trader)
        stop_loss_5.update(order_type=TraderOrderType.STOP_LOSS,
                           symbol="BTC/USDT",
                           current_price=decimal.Decimal(str(9)),
                           quantity=decimal.Decimal(str(0.7)),
                           price=decimal.Decimal(str(9)))

        portfolio_manager.portfolio.update_portfolio_available(stop_loss_2, True)
        portfolio_manager.portfolio.update_portfolio_available(stop_loss_3, True)
        portfolio_manager.portfolio.update_portfolio_available(stop_loss_4, True)
        portfolio_manager.portfolio.update_portfolio_available(stop_loss_5, True)
        with mock.patch.object(exchange_manager.exchange.connector, "_get_fees_currency", return_value="BTC") \
             as _get_fees_currency_mock:
            portfolio_manager.portfolio.update_portfolio_available(limit_sell, True)
            _get_fees_currency_mock.assert_called_once()
        portfolio_manager.portfolio.update_portfolio_available(limit_sell_2, True)
        portfolio_manager.portfolio.update_portfolio_available(limit_sell_3, True)
        portfolio_manager.portfolio.update_portfolio_available(limit_sell_4, True)
        portfolio_manager.portfolio.update_portfolio_available(limit_sell_5, True)
        with mock.patch.object(exchange_manager.exchange.connector, "_get_fees_currency", return_value="USDT") \
             as _get_fees_currency_mock:
            portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)
            _get_fees_currency_mock.assert_called_once()
            _get_fees_currency_mock.reset_mock()
            portfolio_manager.portfolio.update_portfolio_available(limit_buy_2, True)
            _get_fees_currency_mock.assert_called_once()
        portfolio_manager.portfolio.update_portfolio_available(limit_buy_3, True)
        portfolio_manager.portfolio.update_portfolio_available(limit_buy_4, True)
        portfolio_manager.portfolio.update_portfolio_available(limit_buy_5, True)
        portfolio_manager.portfolio.update_portfolio_available(limit_buy_6, True)

        assert round(portfolio_manager.portfolio.get_currency_portfolio("BTC").available,
                     1) == decimal.Decimal('2.1')
        assert round(portfolio_manager.portfolio.get_currency_portfolio("USDT").available,
                     7) == decimal.Decimal('62.4095063')
        assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
        assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

        # cancels
        portfolio_manager.portfolio.update_portfolio_available(stop_loss_3, False)
        portfolio_manager.portfolio.update_portfolio_available(stop_loss_5, False)
        portfolio_manager.portfolio.update_portfolio_available(limit_sell_2, False)
        with mock.patch.object(exchange_manager.exchange.connector, "_get_fees_currency", return_value="USDT") \
             as _get_fees_currency_mock:
            portfolio_manager.portfolio.update_portfolio_available(limit_buy, False)
            _get_fees_currency_mock.assert_called_once()
        portfolio_manager.portfolio.update_portfolio_available(limit_buy_3, False)
        portfolio_manager.portfolio.update_portfolio_available(limit_buy_5, False)
        portfolio_manager.portfolio.update_portfolio_available(limit_sell_4, False)

        assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('4.296')
        assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('275.32')
        assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
        assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000.0000000')

        # filling
        await fill_limit_or_stop_order(stop_loss_2)
        with mock.patch.object(exchange_manager.exchange.connector, "_get_fees_currency", return_value="BTC") \
             as _get_fees_currency_mock:
            await fill_limit_or_stop_order(limit_sell)
            # called twice: once for filled order fee calculation, once for forecasted fees calculation used to restore
            # available amounts if relevant
            assert _get_fees_currency_mock.call_count == 2
        await fill_limit_or_stop_order(limit_sell_3)
        with mock.patch.object(exchange_manager.exchange.connector, "_get_fees_currency", return_value="USDT") \
             as _get_fees_currency_mock:
            await fill_limit_or_stop_order(limit_buy_2)
            # called twice: once for filled order fee calculation, once for forecasted fees calculation used to restore
            # available amounts if relevant
            assert _get_fees_currency_mock.call_count == 2
        await fill_limit_or_stop_order(limit_sell_5)
        await fill_limit_or_stop_order(stop_loss_4)
        await fill_limit_or_stop_order(limit_buy_4)
        await fill_limit_or_stop_order(limit_buy_6)

        assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('9.32317')
        assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('673.9633')
        assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('9.32317')
        assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('673.9633')


async def test_update_portfolio_with_multiple_symbols_orders(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    # Test buy order
    market_buy = BuyMarketOrder(trader)
    market_buy.update(order_type=TraderOrderType.BUY_MARKET,
                      symbol="ETH/USDT",
                      current_price=decimal.Decimal(str(7)),
                      quantity=decimal.Decimal(str(100)),
                      price=decimal.Decimal(str(7)))

    # test buy order creation
    portfolio_manager.portfolio.update_portfolio_available(market_buy, True)
    assert portfolio_manager.portfolio.get_currency_portfolio("ETH").available == decimal.Decimal('0')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('300')
    assert portfolio_manager.portfolio.get_currency_portfolio("ETH").total == decimal.Decimal('0')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    await fill_market_order(market_buy)

    assert portfolio_manager.portfolio.get_currency_portfolio("ETH").available == decimal.Decimal('100')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('300')
    assert portfolio_manager.portfolio.get_currency_portfolio("ETH").total == decimal.Decimal('100')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('300')

    # Test buy order
    market_buy = BuyMarketOrder(trader)
    market_buy.update(order_type=TraderOrderType.BUY_MARKET,
                      symbol="LTC/BTC",
                      current_price=decimal.Decimal(str(0.0135222)),
                      quantity=decimal.Decimal(str(100)),
                      price=decimal.Decimal(str(0.0135222)))

    # test buy order creation
    portfolio_manager.portfolio.update_portfolio_available(market_buy, True)
    assert portfolio_manager.portfolio.get_currency_portfolio("LTC").available == decimal.Decimal('0')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('8.64778')
    assert portfolio_manager.portfolio.get_currency_portfolio("LTC").total == decimal.Decimal('0')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')

    await fill_market_order(market_buy)

    assert portfolio_manager.portfolio.get_currency_portfolio("LTC").available == decimal.Decimal('100')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('8.64778')
    assert portfolio_manager.portfolio.get_currency_portfolio("LTC").total == decimal.Decimal('100')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('8.64778')

    # Test buy order
    limit_buy = BuyLimitOrder(trader)
    limit_buy.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="XRP/BTC",
                     current_price=decimal.Decimal(str(0.00012232132312312)),
                     quantity=decimal.Decimal(str(3000.1214545)),
                     price=decimal.Decimal(str(0.00012232132312312)))

    # test buy order creation
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)
    assert portfolio_manager.portfolio.get_currency_portfolio("XRP").available == decimal.Decimal('0')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('8.280801174155500743021960')
    assert portfolio_manager.portfolio.get_currency_portfolio("XRP").total == decimal.Decimal('0')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('8.64778')

    # cancel
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, False)
    assert portfolio_manager.portfolio.get_currency_portfolio("XRP").available == decimal.Decimal('0')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('8.64778')
    assert portfolio_manager.portfolio.get_currency_portfolio("XRP").total == decimal.Decimal('0')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('8.64778')


async def test_reset_portfolio_available(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    # Test buy order
    limit_sell = SellLimitOrder(trader)
    limit_sell.update(order_type=TraderOrderType.SELL_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal(str(90)),
                      quantity=decimal.Decimal(str(4)),
                      price=decimal.Decimal(str(90)))

    portfolio_manager.portfolio.update_portfolio_available(limit_sell, True)
    portfolio_manager.portfolio.reset_portfolio_available()

    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal(
        '10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal(
        '1000')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal(
        '10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal(
        '1000')

    # Test sell order
    limit_sell = SellLimitOrder(trader)
    limit_sell.update(order_type=TraderOrderType.SELL_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal(str(90)),
                      quantity=decimal.Decimal(str(4)),
                      price=decimal.Decimal(str(90)))

    portfolio_manager.portfolio.update_portfolio_available(limit_sell, True)
    # Test buy order
    limit_buy = BuyLimitOrder(trader)
    limit_buy.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="ADA/BTC",
                     current_price=decimal.Decimal(str(0.5)),
                     quantity=decimal.Decimal(str(4)),
                     price=decimal.Decimal(str(0.5)))

    portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)

    # Test buy order
    btc_limit_buy = BuyLimitOrder(trader)
    btc_limit_buy.update(order_type=TraderOrderType.BUY_LIMIT,
                         symbol="BTC/USDT",
                         current_price=decimal.Decimal(str(10)),
                         quantity=decimal.Decimal(str(50)),
                         price=decimal.Decimal(str(10)))

    portfolio_manager.portfolio.update_portfolio_available(btc_limit_buy, True)

    # Test buy order
    btc_limit_buy2 = BuyLimitOrder(trader)
    btc_limit_buy2.update(order_type=TraderOrderType.BUY_LIMIT,
                          symbol="BTC/USDT",
                          current_price=decimal.Decimal(str(10)),
                          quantity=decimal.Decimal(str(50)),
                          price=decimal.Decimal(str(10)))

    portfolio_manager.portfolio.update_portfolio_available(btc_limit_buy2, True)

    # reset equivalent of the ven buy order
    portfolio_manager.portfolio.reset_portfolio_available("BTC", decimal.Decimal(str(4 * 0.5)))

    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal(
        '6')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal(
        '10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal(
        '0')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal(
        '1000')

    # reset equivalent of the btc buy orders 1 and 2
    portfolio_manager.portfolio.reset_portfolio_available("USDT")

    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal(
        '6')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal(
        '10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal(
        '1000')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal(
        '1000')


async def test_default_impl(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    order = BuyMarketOrder(trader)
    order.symbol = "BTC/USDT"

    # should not raise NotImplemented
    portfolio_manager.portfolio.update_portfolio_data_from_order(order)
    portfolio_manager.portfolio.update_portfolio_available_from_order(order)
    portfolio_manager.portfolio.log_portfolio_update_from_order(order)


async def test_parse_currency_balance(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    if not os.getenv('CYTHON_IGNORE'):
        # 0 values
        parsed_portfolio = portfolio_manager.portfolio._parse_raw_currency_asset("BTC",
            {commons_constants.PORTFOLIO_AVAILABLE: constants.ZERO,
             commons_constants.PORTFOLIO_TOTAL: constants.ZERO})
        assert parsed_portfolio.available == constants.ZERO
        assert parsed_portfolio.total == constants.ZERO

        parsed_portfolio_2 = portfolio_manager.portfolio._parse_raw_currency_asset("BTC",
            {constants.CONFIG_PORTFOLIO_FREE: constants.ZERO,
             commons_constants.PORTFOLIO_TOTAL: constants.ZERO})
        assert parsed_portfolio_2.available == constants.ZERO
        assert parsed_portfolio_2.total == constants.ZERO

        # None values
        parsed_portfolio_3 = portfolio_manager.portfolio._parse_raw_currency_asset("BTC",
            {commons_constants.PORTFOLIO_AVAILABLE: None,
             commons_constants.PORTFOLIO_TOTAL: constants.ZERO})
        assert parsed_portfolio_3.available == constants.ZERO
        assert parsed_portfolio_3.total == constants.ZERO

        parsed_portfolio_4 = portfolio_manager.portfolio._parse_raw_currency_asset("BTC",
            {commons_constants.PORTFOLIO_AVAILABLE: None,
             commons_constants.PORTFOLIO_TOTAL: None})
        assert parsed_portfolio_4.available == constants.ZERO
        assert parsed_portfolio_4.total == constants.ZERO

        parsed_portfolio_5 = portfolio_manager.portfolio._parse_raw_currency_asset("BTC",
            {commons_constants.PORTFOLIO_AVAILABLE: constants.ZERO,
             commons_constants.PORTFOLIO_TOTAL: None})
        assert parsed_portfolio_5.available == constants.ZERO
        assert parsed_portfolio_5.total == constants.ZERO

        parsed_portfolio_6 = portfolio_manager.portfolio._parse_raw_currency_asset("BTC",
             {constants.CONFIG_PORTFOLIO_FREE: None,
              commons_constants.PORTFOLIO_TOTAL: 0.0})
        assert parsed_portfolio_6.available == constants.ZERO
        assert parsed_portfolio_6.total == constants.ZERO

        parsed_portfolio_7 = portfolio_manager.portfolio._parse_raw_currency_asset("BTC",
             {constants.CONFIG_PORTFOLIO_FREE: None,
             commons_constants.PORTFOLIO_TOTAL: None})
        assert parsed_portfolio_7.available == constants.ZERO
        assert parsed_portfolio_7.total == constants.ZERO

        parsed_portfolio_8 = portfolio_manager.portfolio._parse_raw_currency_asset("BTC",
            {constants.CONFIG_PORTFOLIO_FREE: constants.ZERO,
             commons_constants.PORTFOLIO_TOTAL: None})
        assert parsed_portfolio_8.available == constants.ZERO
        assert parsed_portfolio_8.total == constants.ZERO


async def test_update_portfolio_data(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    if not os.getenv('CYTHON_IGNORE'):
        # doesn't raise
        portfolio_manager.portfolio._update_portfolio_data("BTC", -1)

        with pytest.raises(errors.PortfolioNegativeValueError):
            portfolio_manager.portfolio._update_portfolio_data("USDT", decimal.Decimal(-2000))
        with pytest.raises(errors.PortfolioNegativeValueError):
            portfolio_manager.portfolio._update_portfolio_data("BTC", decimal.Decimal(-20))

    if not os.getenv('CYTHON_IGNORE'):
        with pytest.raises(errors.PortfolioNegativeValueError):
            # Test buy order
            btc_limit_buy2 = BuyLimitOrder(trader)
            btc_limit_buy2.update(order_type=TraderOrderType.BUY_LIMIT,
                                  symbol="BTC/USDT",
                                  current_price=decimal.Decimal("10"),
                                  quantity=decimal.Decimal("5000000000"),
                                  price=decimal.Decimal("10"))

            portfolio_manager.portfolio.update_portfolio_available(btc_limit_buy2, True)
