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
import decimal
import mock
import pytest

import octobot_trading.enums
import octobot_trading.personal_data as personal_data
from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_initial_portfolio(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    assert isinstance(portfolio_manager.portfolio, personal_data.SpotPortfolio)


async def test_update_portfolio_data_from_order(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    pass


async def test_update_portfolio_available_from_order(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    # Test buy order
    market_buy = personal_data.BuyMarketOrder(trader)
    market_buy.update(order_type=octobot_trading.enums.TraderOrderType.BUY_MARKET,
                      symbol="BTC/USDT",
                      current_price=70,
                      quantity=10,
                      price=70)

    # test buy order creation
    portfolio_manager.portfolio.update_portfolio_available(market_buy, True)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('300')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # test buy order canceled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
    portfolio_manager.portfolio.update_portfolio_available(market_buy, False)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # Test sell order
    limit_sell = personal_data.SellLimitOrder(trader)
    limit_sell.update(order_type=octobot_trading.enums.TraderOrderType.SELL_LIMIT,
                      symbol="BTC/USDT",
                      current_price=60,
                      quantity=8,
                      price=60)

    # test sell order creation
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, True)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('2')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # test sell order canceled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, False)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # Test buy order with large USDT fee
    limit_buy = personal_data.BuyLimitOrder(trader)
    limit_buy.update(order_type=octobot_trading.enums.TraderOrderType.BUY_LIMIT,
                      symbol="BTC/USDT",
                      current_price=60,
                      quantity=8,
                      quantity_filled=8,
                      price=60)
    fee = {
        octobot_trading.enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: True,
        octobot_trading.enums.FeePropertyColumns.COST.value: 54.111111,
        octobot_trading.enums.FeePropertyColumns.CURRENCY.value: "USDT",
    }

    # even if order is filled, always update available funds with use_origin_quantity_and_price and taker fees
    with (mock.patch.object(limit_buy, "is_filled", mock.Mock(return_value=True)) as is_filled_value_mock,
          mock.patch.object(limit_buy.exchange_manager.exchange, "get_trade_fee", mock.Mock(return_value=fee)) as get_trade_fee_mock):
        # test buy order creation
        portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)
        get_trade_fee_mock.assert_called_once_with(
            limit_buy.symbol, limit_buy.order_type, limit_buy.origin_quantity, limit_buy.origin_price,
            octobot_trading.enums.ExchangeConstantsOrderColumns.TAKER.value,
        )
        get_trade_fee_mock.reset_mock()
        is_filled_value_mock.assert_called_once()
        is_filled_value_mock.reset_mock()
        assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
        # cost with fees = 60 * 8 + 54.111111 = 534.111111
        assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == (
            decimal.Decimal('1000') - decimal.Decimal('534.111111')
        )
        assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
        assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

        # test buy order canceled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
        portfolio_manager.portfolio.update_portfolio_available(limit_buy, False)
        get_trade_fee_mock.assert_called_once_with(
            limit_buy.symbol, limit_buy.order_type, limit_buy.origin_quantity, limit_buy.origin_price,
            octobot_trading.enums.ExchangeConstantsOrderColumns.TAKER.value,
        )
        get_trade_fee_mock.reset_mock()
        is_filled_value_mock.assert_called_once()
        is_filled_value_mock.reset_mock()
        assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
        assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')
        assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
        assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')


async def test_update_portfolio_available_from_partially_filled_orders(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    # Test buy order
    limit_buy = personal_data.BuyLimitOrder(trader)
    limit_buy.update(order_type=octobot_trading.enums.TraderOrderType.BUY_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal('70'),
                      quantity=decimal.Decimal('10'),
                      quantity_filled=decimal.Decimal('3'),
                      price=decimal.Decimal('70'))

    already_filled_cost = limit_buy.get_cost(limit_buy.filled_quantity)
    assert already_filled_cost == decimal.Decimal('210')
    assert limit_buy.get_locked_quantity() == decimal.Decimal('7') # 10 - 3
    # test buy order creation
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, True)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
    # already_filled_cost is not taken from available funds
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('300') + already_filled_cost
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    # in this test, total funds have not been updated to account for already filled cost, so it's still 1000
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # test buy order canceled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
    portfolio_manager.portfolio.update_portfolio_available(limit_buy, False)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # Test sell order
    limit_sell = personal_data.SellLimitOrder(trader)
    limit_sell.update(order_type=octobot_trading.enums.TraderOrderType.SELL_LIMIT,
                      symbol="BTC/USDT",
                      current_price=decimal.Decimal('60'),
                      quantity=decimal.Decimal('8'),
                      quantity_filled=decimal.Decimal('7.5'),
                      price=decimal.Decimal('60'))

    already_filled_cost = limit_sell.get_cost(limit_sell.filled_quantity)
    assert already_filled_cost == decimal.Decimal('450')    # 7.5 * 60
    assert limit_sell.get_locked_quantity() == decimal.Decimal('0.5') # 8 - 7.5

    # test sell order creation
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, True)
    # 0.5 locked as other 7.5 have already been sold, they are not locked anymore
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10') - decimal.Decimal('0.5')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')
    # in this test, total has not been updated to account for already filled amount, so it's still 10
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # test sell order canceled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
    portfolio_manager.portfolio.update_portfolio_available(limit_sell, False)
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").available == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')
    assert portfolio_manager.portfolio.get_currency_portfolio("BTC").total == decimal.Decimal('10')
    assert portfolio_manager.portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')
