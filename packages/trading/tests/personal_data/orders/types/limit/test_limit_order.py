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

import octobot_trading.enums as enums

import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as trading_personal_data
from tests.personal_data import DEFAULT_MARKET_QUANTITY, DEFAULT_ORDER_SYMBOL
from tests.test_utils.random_numbers import decimal_random_quantity

from tests import event_loop
from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests.personal_data.orders import backtesting_buy_and_sell_limit_orders

pytestmark = pytest.mark.asyncio


async def test_update_price_if_outdated(backtesting_buy_and_sell_limit_orders):
    buy_limit_order, sell_limit_order = backtesting_buy_and_sell_limit_orders
    buy_order_price = decimal.Decimal("100")
    buy_limit_order.update(
        price=buy_order_price,
        quantity=decimal_random_quantity(max_value=DEFAULT_MARKET_QUANTITY / buy_order_price),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.BUY_LIMIT,
    )
    sell_order_price = decimal.Decimal("150")
    sell_limit_order.update(
        price=sell_order_price,
        quantity=decimal_random_quantity(max_value=DEFAULT_MARKET_QUANTITY / sell_order_price),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.BUY_LIMIT,
    )
    origin_update_limit_price_if_necessary = buy_limit_order._update_limit_price_if_necessary
    # buy side
    with mock.patch.object(
        buy_limit_order, "_update_limit_price_if_necessary",
        mock.Mock(side_effect=origin_update_limit_price_if_necessary)
    ) as _update_limit_price_if_necessary_mock:
        # without price
        await buy_limit_order.update_price_if_outdated()
        _update_limit_price_if_necessary_mock.assert_not_called()

        # with up-to-date price
        buy_limit_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(buy_limit_order.symbol).\
            prices_manager.set_mark_price(decimal.Decimal("110"), enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value)
        await buy_limit_order.update_price_if_outdated()
        _update_limit_price_if_necessary_mock.assert_called_once()
        assert buy_limit_order.origin_price is buy_order_price
        _update_limit_price_if_necessary_mock.reset_mock()

        # with outdated price
        buy_limit_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(buy_limit_order.symbol).\
            prices_manager.set_mark_price(decimal.Decimal("90"), enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value)
        await buy_limit_order.update_price_if_outdated()

        _update_limit_price_if_necessary_mock.assert_called_once()
        # price got adapted
        assert buy_limit_order.origin_price < buy_order_price
        assert buy_limit_order.origin_price == decimal.Decimal("90") * (
            trading_constants.ONE + trading_constants.CHAINED_ORDERS_OUTDATED_PRICE_ALLOWANCE
        )

    sell_limit_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(sell_limit_order.symbol). \
        prices_manager._reset_prices()
    origin_update_limit_price_if_necessary = sell_limit_order._update_limit_price_if_necessary
    # sell side
    with mock.patch.object(
        sell_limit_order, "_update_limit_price_if_necessary",
        mock.Mock(side_effect=origin_update_limit_price_if_necessary)
    ) as _update_limit_price_if_necessary_mock:
        # without price
        await sell_limit_order.update_price_if_outdated()
        _update_limit_price_if_necessary_mock.assert_not_called()

        # with up-to-date price
        sell_limit_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(sell_limit_order.symbol).\
            prices_manager.set_mark_price(decimal.Decimal("110"), enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value)
        await sell_limit_order.update_price_if_outdated()
        _update_limit_price_if_necessary_mock.assert_called_once()
        assert sell_limit_order.origin_price is sell_order_price
        _update_limit_price_if_necessary_mock.reset_mock()

        # with outdated price
        not_round_price = decimal.Decimal("155") + decimal.Decimal(1/3)  # force not round number
        sell_limit_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(sell_limit_order.symbol).\
            prices_manager.set_mark_price(not_round_price, enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value)
        await sell_limit_order.update_price_if_outdated()

        _update_limit_price_if_necessary_mock.assert_called_once()
        # price got adapted
        assert sell_limit_order.origin_price > sell_order_price
        assert sell_limit_order.origin_price != not_round_price * (
            trading_constants.ONE - trading_constants.CHAINED_ORDERS_OUTDATED_PRICE_ALLOWANCE
        )
        # ensure price decimals got adapted
        assert sell_limit_order.origin_price == trading_personal_data.decimal_adapt_price(
            sell_limit_order.exchange_manager.exchange.get_market_status(sell_limit_order.symbol, with_fixer=False),
            not_round_price * (
                trading_constants.ONE - trading_constants.CHAINED_ORDERS_OUTDATED_PRICE_ALLOWANCE
            )
        )

async def test_filled_maker_or_taker(backtesting_buy_and_sell_limit_orders):
    buy_limit_order, sell_limit_order = backtesting_buy_and_sell_limit_orders
    buy_order_price = decimal.Decimal("100")
    buy_limit_order.update(
        price=buy_order_price,
        quantity=decimal_random_quantity(max_value=DEFAULT_MARKET_QUANTITY / buy_order_price),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=enums.TraderOrderType.BUY_LIMIT,
    )
    assert buy_limit_order._filled_maker_or_taker() == enums.ExchangeConstantsMarketPropertyColumns.MAKER.value
    buy_limit_order.created_last_price = decimal.Decimal("99")
    assert buy_limit_order._filled_maker_or_taker() == enums.ExchangeConstantsMarketPropertyColumns.TAKER.value
    await buy_limit_order.set_as_chained_order(sell_limit_order, False, {}, False)
    sell_limit_order.origin_price = decimal.Decimal("101")
    # now uses trigger order filling price
    assert buy_limit_order._filled_maker_or_taker() == enums.ExchangeConstantsMarketPropertyColumns.MAKER.value
