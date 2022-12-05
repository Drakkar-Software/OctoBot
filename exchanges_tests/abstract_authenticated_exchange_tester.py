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
import contextlib
import decimal
import time

import octobot_commons.constants as constants
import octobot_commons.symbols as symbols
import octobot_commons.enums as commons_enums
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as personal_data
import octobot_tentacles_manager.api as tentacles_manager_api
from exchanges_tests import get_authenticated_exchange_manager

import tentacles


tentacles_manager_api.reload_tentacle_info()


class AbstractAuthenticatedExchangeTester:
    # enter exchange name as a class variable here
    EXCHANGE_NAME = None
    EXCHANGE_TENTACLE_NAME = None
    EXCHANGE_TYPE = trading_enums.ExchangeTypes.SPOT.value
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 10  # % of portfolio to include in test orders
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}"
    ORDER_PRICE_DIFF = 10  # % of price difference compared to current price for limit orders
    MARKET_FILL_TIMEOUT = 15


    async def test_get_portfolio(self):
        pass

    async def test_create_limit_orders(self):
        pass

    async def test_create_market_orders(self):
        pass

    async def test_create_stop_orders(self):
        pass

    async def test_create_bundled_orders(self):
        pass

    async def get_position(self, symbol=None):
        return await self.exchange_manager.exchange.get_position(symbol or self.SYMBOL)

    async def get_portfolio(self):
        return await self.exchange_manager.exchange.get_balance()

    async def get_price(self, symbol=None):
        return decimal.Decimal(str(
            (await self.exchange_manager.exchange.get_price_ticker(symbol or self.SYMBOL))[
                trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
            ]
        ))

    @contextlib.asynccontextmanager
    async def local_exchange_manager(self):
        try:
            exchange_tentacle_name = self.EXCHANGE_TENTACLE_NAME or self.EXCHANGE_NAME.capitalize()
            async with get_authenticated_exchange_manager(self.EXCHANGE_NAME, exchange_tentacle_name,
                                                          self.get_config()) as exchange_manager:
                self.exchange_manager = exchange_manager
                yield
        finally:
            self.exchange_manager = None

    def check_portfolio_content(self, portfolio):
        assert len(portfolio) > 0
        at_least_one_value = False
        for asset, values in portfolio.items():
            assert all(
                key in values
                for key in (
                    trading_constants.CONFIG_PORTFOLIO_FREE,
                    trading_constants.CONFIG_PORTFOLIO_USED,
                    trading_constants.CONFIG_PORTFOLIO_TOTAL
                )
            )
            if values[trading_constants.CONFIG_PORTFOLIO_TOTAL] > trading_constants.ZERO:
                at_least_one_value = True
        assert at_least_one_value

    async def create_limit_order(self, price, size, side, symbol=None):
        current_order = personal_data.create_order_instance(
            self.exchange_manager.trader,
            order_type=trading_enums.TraderOrderType.BUY_LIMIT
            if side is trading_enums.TradeOrderSide.BUY else trading_enums.TraderOrderType.SELL_LIMIT,
            symbol=symbol or self.SYMBOL,
            current_price=price,
            quantity=size,
            price=price,
        )
        return await self.exchange_manager.trader.create_order(current_order)

    async def create_market_order(self, size, side, symbol=None):
        current_order = personal_data.create_order_instance(
            self.exchange_manager.trader,
            order_type=trading_enums.TraderOrderType.BUY_MARKET
            if side is trading_enums.TradeOrderSide.BUY else trading_enums.TraderOrderType.SELL_MARKET,
            symbol=symbol or self.SYMBOL,
            quantity=size,
        )
        return await self.exchange_manager.trader.create_order(current_order)

    def get_order_size(self, portfolio, price, symbol=None):
        currency_quantity = portfolio[self.SETTLEMENT_CURRENCY][trading_constants.CONFIG_PORTFOLIO_TOTAL] \
            * decimal.Decimal(self.ORDER_SIZE) / trading_constants.ONE_HUNDRED
        symbol = symbols.parse_symbol(symbol or self.SYMBOL)
        if symbol.is_inverse():
            order_quantity = currency_quantity * price
        else:
            order_quantity = currency_quantity / price
        return personal_data.decimal_adapt_quantity(
            self.exchange_manager.exchange.get_market_status(str(symbol)),
            order_quantity
        )

    def get_order_price(self, price, is_above_price, symbol=None):
        multiplier = 1 + self.ORDER_PRICE_DIFF / 100 if is_above_price else 1 - self.ORDER_PRICE_DIFF / 100
        return personal_data.decimal_adapt_price(
            self.exchange_manager.exchange.get_market_status(symbol or self.SYMBOL),
            price * (decimal.Decimal(str(multiplier)))
        )

    async def get_open_orders(self, symbol=None):
        return await self.exchange_manager.exchange.get_open_orders(symbol)

    def check_created_limit_order(self, order, price, size, side):
        self._check_order(order, size, side)
        assert order.origin_price == price
        expected_type = personal_data.BuyLimitOrder \
            if side is trading_enums.TradeOrderSide.BUY else personal_data.SellLimitOrder
        assert isinstance(order, expected_type)

    def check_created_market_order(self, order, size, side):
        self._check_order(order, size, side)
        expected_type = personal_data.BuyMarketOrder \
            if side is trading_enums.TradeOrderSide.BUY else personal_data.SellMarketOrder
        assert isinstance(order, expected_type)

    async def check_position_changed(self, previous_position, has_increased, symbol=None):
        updated_position = await self.get_position(symbol)
        if previous_position is None:
            assert updated_position[trading_enums.ExchangePositionCCXTColumns.NOTIONAL.value] > 0
        # todo

    def _check_order(self, order, size, side):
        assert order.origin_quantity == size
        assert order.side is side
        assert order.is_open()

    async def wait_for_filling(self, order):
        t0 = time.time()
        while time.time() - t0 < self.MARKET_FILL_TIMEOUT:
            order = await self.exchange_manager.exchange.get_order(order.order_id)
            if order and personal_data.parse_is_cancelled(order):
                return
        raise TimeoutError(f"Order not filled within {self.MARKET_FILL_TIMEOUT}s: {order}")

    async def order_in_open_orders(self, previous_open_orders, order):
        open_orders = await self.get_open_orders()
        assert len(open_orders) == len(previous_open_orders) + 1
        for open_order in open_orders:
            if open_order[trading_enums.ExchangeConstantsOrderColumns.ID.value] == order.order_id:
                return True
        return False

    async def order_not_in_open_orders(self, previous_open_orders, order):
        open_orders = await self.get_open_orders()
        assert len(open_orders) == len(previous_open_orders)
        for open_order in open_orders:
            if open_order[trading_enums.ExchangeConstantsOrderColumns.ID.value] == order.order_id:
                return False
        return True

    async def cancel_order(self, order):
        return await self.exchange_manager.trader.cancel_order(order)

    def get_config(self):
        return {
            constants.CONFIG_EXCHANGES: {
                self.EXCHANGE_NAME: {
                    constants.CONFIG_EXCHANGE_TYPE: self.EXCHANGE_TYPE
                }
            }
        }
