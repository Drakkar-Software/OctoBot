#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import pytest

import octobot_trading.enums as trading_enums
from exchanges_tests import abstract_authenticated_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestBybitAuthenticatedExchange(abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester):
    # enter exchange name as a class variable here
    EXCHANGE_NAME = "bybit"
    EXCHANGE_TYPE = trading_enums.ExchangeTypes.FUTURE.value
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 10  # % of portfolio to include in test orders
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}:{SETTLEMENT_CURRENCY}"

    async def _test_get_portfolio(self):
        async with self.local_exchange_manager():
            self.check_portfolio_content(await self.get_portfolio())

    async def test_create_limit_orders(self):
        async with self.local_exchange_manager():
            position = await self.get_position()
            portfolio = await self.get_portfolio()
            symbol_price = await self.get_price()
            price = self.get_order_price(symbol_price, False)
            size = self.get_order_size(portfolio, price)
            open_orders = await self.get_open_orders()
            buy_limit = await self.create_limit_order(price, size, trading_enums.TradeOrderSide.BUY)
            # todo add opening state
            self.check_created_limit_order(buy_limit, price, size, trading_enums.TradeOrderSide.BUY)
            assert await self.order_in_open_orders(open_orders, buy_limit)
            await self.cancel_order(buy_limit)
            # todo add cancelling state
            assert await self.order_not_in_open_orders(open_orders, buy_limit)

    async def test_create_market_orders(self):
        async with self.local_exchange_manager():
            position = await self.get_position()
            portfolio = await self.get_portfolio()
            symbol_price = await self.get_price()
            price = self.get_order_price(symbol_price, False)
            size = self.get_order_size(portfolio, price)
            buy_market = await self.create_market_order(size, trading_enums.TradeOrderSide.BUY)
            self.check_created_market_order(buy_market, size, trading_enums.TradeOrderSide.BUY)
            await self.wait_for_filling(buy_market)
            await self.check_position_changed(position, True)



    async def test_create_stop_orders(self):
        pass

    async def test_create_bundled_orders(self):
        pass
