#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as personal_data
import octobot_trading.personal_data.orders as personal_data_orders
import octobot_tentacles_manager.api as tentacles_manager_api
from exchanges_tests import get_authenticated_exchange_manager

# always import and load tentacles
import tentacles
tentacles_manager_api.reload_tentacle_info()


class AbstractAuthenticatedExchangeTester:
    # enter exchange name as a class variable here
    EXCHANGE_NAME = None
    EXCHANGE_TENTACLE_NAME = None
    EXCHANGE_TYPE = trading_enums.ExchangeTypes.SPOT.value
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}"
    ORDER_SIZE = 10  # % of portfolio to include in test orders
    PORTFOLIO_TYPE_FOR_SIZE = trading_constants.CONFIG_PORTFOLIO_FREE
    CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = False
    ORDER_PRICE_DIFF = 20  # % of price difference compared to current price for limit and stop orders
    NO_FEE_ON_GET_CLOSED_ORDERS = False
    OPEN_ORDERS_IN_CLOSED_ORDERS = False
    MARKET_FILL_TIMEOUT = 15
    OPEN_TIMEOUT = 15
    CANCEL_TIMEOUT = 15
    EDIT_TIMEOUT = 15

    # Implement all "test_[name]" methods, call super() to run the test, pass to ignore it.
    # Override the "inner_test_[name]" method to override a test content.
    # Add method call to subclasses to be able to run them independently

    async def test_get_portfolio(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_portfolio()

    async def inner_test_get_portfolio(self):
        self.check_portfolio_content(await self.get_portfolio())

    async def test_create_and_cancel_limit_orders(self):
        async with self.local_exchange_manager():
            await self.inner_test_create_and_cancel_limit_orders()

    async def inner_test_create_and_cancel_limit_orders(self):
        price = self.get_order_price(await self.get_price(), False)
        size = self.get_order_size(await self.get_portfolio(), price)
        open_orders = await self.get_open_orders()
        buy_limit = await self.create_limit_order(price, size, trading_enums.TradeOrderSide.BUY)
        self.check_created_limit_order(buy_limit, price, size, trading_enums.TradeOrderSide.BUY)
        assert await self.order_in_open_orders(open_orders, buy_limit)
        await self.cancel_order(buy_limit)
        assert await self.order_not_in_open_orders(open_orders, buy_limit)

    async def test_create_and_fill_market_orders(self):
        async with self.local_exchange_manager():
            await self.inner_test_create_and_fill_market_orders()

    async def inner_test_create_and_fill_market_orders(self):
        portfolio = await self.get_portfolio()
        current_price = await self.get_price()
        price = self.get_order_price(current_price, False)
        size = self.get_order_size(portfolio, price)
        buy_market = await self.create_market_order(current_price, size, trading_enums.TradeOrderSide.BUY)
        self.check_created_market_order(buy_market, size, trading_enums.TradeOrderSide.BUY)
        await self.wait_for_fill(buy_market)
        sell_size = self.get_sell_size_from_buy_order(buy_market)
        post_buy_portfolio = await self.get_portfolio()
        self.check_portfolio_changed(portfolio, post_buy_portfolio, False)
        # sell: reset portfolio
        sell_market = await self.create_market_order(current_price, sell_size, trading_enums.TradeOrderSide.SELL)
        self.check_created_market_order(sell_market, sell_size, trading_enums.TradeOrderSide.SELL)
        await self.wait_for_fill(sell_market)
        post_sell_portfolio = await self.get_portfolio()
        self.check_portfolio_changed(post_buy_portfolio, post_sell_portfolio, True)

    async def test_create_and_cancel_stop_orders(self):
        # pass if not implemented
        async with self.local_exchange_manager():
            await self.inner_test_create_and_cancel_stop_orders()

    async def inner_test_create_and_cancel_stop_orders(self):
        current_price = await self.get_price()
        price = self.get_order_price(current_price, False)
        size = self.get_order_size(await self.get_portfolio(), price)
        open_orders = await self.get_open_orders()
        stop_loss = await self.create_market_stop_loss_order(current_price, price, size,
                                                             trading_enums.TradeOrderSide.SELL)
        self.check_created_stop_order(stop_loss, price, size, trading_enums.TradeOrderSide.SELL)
        stop_loss_from_get_order = await self.get_order(stop_loss.order_id)
        self.check_created_stop_order(stop_loss_from_get_order, price, size, trading_enums.TradeOrderSide.SELL)
        assert await self.order_in_open_orders(open_orders, stop_loss)
        await self.cancel_order(stop_loss)
        assert await self.order_not_in_open_orders(open_orders, stop_loss)

    async def test_get_my_recent_trades(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_my_recent_trades()

    async def inner_test_get_my_recent_trades(self):
        trades = await self.get_my_recent_trades()
        assert trades
        self.check_raw_trades(trades)

    async def test_get_closed_orders(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_closed_orders()

    async def inner_test_get_closed_orders(self):
        orders = await self.get_closed_orders()
        assert orders
        self.check_raw_closed_orders(orders)

    async def test_edit_limit_order(self):
        # pass if not implemented
        async with self.local_exchange_manager():
            await self.inner_test_edit_limit_order()

    async def inner_test_edit_limit_order(self):
        current_price = await self.get_price()
        portfolio = await self.get_portfolio()
        price = self.get_order_price(current_price, True)
        size = self.get_order_size(portfolio, price)
        open_orders = await self.get_open_orders()
        sell_limit = await self.create_limit_order(price, size, trading_enums.TradeOrderSide.SELL)
        self.check_created_limit_order(sell_limit, price, size, trading_enums.TradeOrderSide.SELL)
        assert await self.order_in_open_orders(open_orders, sell_limit)
        edited_price = self.get_order_price(current_price, True, price_diff=2*self.ORDER_PRICE_DIFF)
        edited_size = self.get_order_size(portfolio, price, order_size=2*self.ORDER_SIZE)
        await self.edit_order(sell_limit,
                              edited_price=edited_price,
                              edited_quantity=edited_size)
        await self.wait_for_edit(sell_limit, edited_size)
        sell_limit = await self.get_order(sell_limit.order_id)
        self.check_created_limit_order(sell_limit, edited_price, edited_size, trading_enums.TradeOrderSide.SELL)
        await self.cancel_order(sell_limit)
        assert await self.order_not_in_open_orders(open_orders, sell_limit)

    async def test_edit_stop_order(self):
        # pass if not implemented
        async with self.local_exchange_manager():
            await self.inner_test_edit_stop_order()

    async def inner_test_edit_stop_order(self):
        current_price = await self.get_price()
        portfolio = await self.get_portfolio()
        price = self.get_order_price(current_price, True)
        size = self.get_order_size(portfolio, price)
        open_orders = await self.get_open_orders()
        stop_loss = await self.create_market_stop_loss_order(current_price, price, size,
                                                             trading_enums.TradeOrderSide.SELL)
        self.check_created_stop_order(stop_loss, price, size, trading_enums.TradeOrderSide.SELL)
        assert await self.order_in_open_orders(open_orders, stop_loss)
        edited_price = self.get_order_price(current_price, True, price_diff=2*self.ORDER_PRICE_DIFF)
        edited_size = self.get_order_size(portfolio, price, order_size=2*self.ORDER_SIZE)
        await self.edit_order(stop_loss,
                              edited_stop_price=edited_price,
                              edited_quantity=edited_size)
        await self.wait_for_edit(stop_loss, edited_size)
        stop_loss = await self.get_order(stop_loss.order_id)
        self.check_created_stop_order(stop_loss, edited_price, edited_size, trading_enums.TradeOrderSide.SELL)
        await self.cancel_order(stop_loss)
        assert await self.order_not_in_open_orders(open_orders, stop_loss)

    async def test_create_bundled_orders(self):
        # pass if not implemented
        async with self.local_exchange_manager():
            await self.inner_test_create_bundled_orders()

    async def inner_test_create_bundled_orders(self):
        current_price = await self.get_price()
        stop_loss_price = self.get_order_price(current_price, False)
        take_profit_price = self.get_order_price(current_price, True)
        size = self.get_order_size(await self.get_portfolio(), stop_loss_price)
        open_orders = await self.get_open_orders()
        stop_loss = await self.create_market_stop_loss_order(current_price, stop_loss_price, size,
                                                             trading_enums.TradeOrderSide.SELL,
                                                             push_on_exchange=False)
        take_profit = await self.create_order(take_profit_price, current_price, size, trading_enums.TradeOrderSide.SELL,
                                              trading_enums.TraderOrderType.TAKE_PROFIT, push_on_exchange=False)
        market_order = await self.create_market_order(current_price, size,
                                                      trading_enums.TradeOrderSide.BUY,
                                                      push_on_exchange=False)
        # bundle stop loss and take profits into open position order
        params = await self.exchange_manager.trader.bundle_chained_order_with_uncreated_order(market_order, stop_loss)
        params.update(
            await self.exchange_manager.trader.bundle_chained_order_with_uncreated_order(market_order, take_profit)
        )
        buy_market = await self._create_order_on_exchange(market_order, params=params)
        self.check_created_market_order(buy_market, size, trading_enums.TradeOrderSide.BUY)
        await self.wait_for_fill(buy_market)
        created_orders = [stop_loss, take_profit]
        fetched_conditional_orders = await self.get_similar_orders_in_open_orders(open_orders, created_orders)
        for fetched_conditional_order in fetched_conditional_orders:
            # ensure stop loss / take profit is fetched in open orders
            # ensure stop loss / take profit cancel is working
            await self.cancel_order(fetched_conditional_order)
        for fetched_conditional_order in fetched_conditional_orders:
            assert await self.order_not_in_open_orders(open_orders, fetched_conditional_order)
        # close position
        sell_market = await self.create_market_order(current_price, size,
                                                     trading_enums.TradeOrderSide.SELL)
        self.check_created_market_order(sell_market, size, trading_enums.TradeOrderSide.SELL)
        await self.wait_for_fill(sell_market)

    async def get_portfolio(self):
        return await self.exchange_manager.exchange.get_balance()

    async def get_my_recent_trades(self, symbol=None):
        return await self.exchange_manager.exchange.get_my_recent_trades(symbol or self.SYMBOL)

    async def get_closed_orders(self, symbol=None):
        return await self.exchange_manager.exchange.get_closed_orders(symbol or self.SYMBOL)

    def check_duplicate(self, orders_or_trades):
        assert len({
            f"{o[trading_enums.ExchangeConstantsOrderColumns.ID.value]}"
            f"{o[trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value]}"
            f"{o[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]}"
            f"{o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]}"
            for o in orders_or_trades
        }) == len(orders_or_trades)

    def check_raw_closed_orders(self, closed_orders):
        self.check_duplicate(closed_orders)
        for closed_order in closed_orders:
            self.check_parsed_closed_order(
                personal_data.create_order_instance_from_raw(self.exchange_manager.trader, closed_order)
            )

    def check_parsed_closed_order(self, order: personal_data.Order):
        assert order.symbol
        assert order.timestamp
        assert order.order_type
        assert order.status
        if self.NO_FEE_ON_GET_CLOSED_ORDERS:
            assert order.fee is None
        else:
            assert order.fee
        assert order.order_id
        assert order.side
        if order.status not in (trading_enums.OrderStatus.REJECTED, trading_enums.OrderStatus.CANCELED):
            assert order.origin_quantity
            if self.OPEN_ORDERS_IN_CLOSED_ORDERS and order.status is trading_enums.OrderStatus.OPEN:
                # when order is open, cost is not full
                return
            self.check_theoretical_cost(
                symbols.parse_symbol(order.symbol), order.origin_quantity, order.origin_price, order.total_cost
            )

    def check_raw_trades(self, trades):
        self.check_duplicate(trades)
        for trade in trades:
            self.check_parsed_trade(
                personal_data.create_trade_instance_from_raw(self.exchange_manager.trader, trade)
            )

    def check_parsed_trade(self, trade: personal_data.Trade):
        assert trade.symbol
        assert trade.total_cost
        assert trade.trade_type
        assert trade.status
        assert trade.fee
        assert trade.origin_order_id
        assert trade.side
        if trade.status is not trading_enums.OrderStatus.CANCELED:
            assert trade.executed_quantity
            self.check_theoretical_cost(
                symbols.parse_symbol(trade.symbol), trade.executed_quantity,
                trade.executed_price, trade.total_cost
            )

    def check_theoretical_cost(self, symbol, quantity, price, cost):
        theoretical_cost = quantity * price
        assert theoretical_cost * decimal.Decimal("0.8") <= cost <= theoretical_cost * decimal.Decimal("1.2")

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

    async def get_order(self, order_id, symbol=None):
        return personal_data.create_order_instance_from_raw(
            self.exchange_manager.trader,
            await self.exchange_manager.exchange.get_order(order_id, symbol or self.SYMBOL)
        )

    async def edit_order(self, order,
                         edited_quantity: decimal.Decimal = None,
                         edited_price: decimal.Decimal = None,
                         edited_stop_price: decimal.Decimal = None,
                         edited_current_price: decimal.Decimal = None,
                         params: dict = None):
        edited_order = await self.exchange_manager.exchange.edit_order(
            order.order_id,
            order.order_type,
            order.symbol,
            quantity=order.origin_quantity if edited_quantity is None else edited_quantity,
            price=order.origin_price if edited_price is None else edited_price,
            stop_price=edited_stop_price,
            side=order.side,
            current_price=edited_current_price,
            params=params
        )
        assert edited_order is not None
        return edited_order

    async def create_limit_order(self, price, size, side, symbol=None,
                                 push_on_exchange=True):
        order_type = trading_enums.TraderOrderType.BUY_LIMIT \
            if side is trading_enums.TradeOrderSide.BUY else trading_enums.TraderOrderType.SELL_LIMIT
        return await self.create_order(price, price, size, side, order_type,
                                       symbol=symbol, push_on_exchange=push_on_exchange)

    async def create_market_stop_loss_order(self, current_price, stop_price, size, side, symbol=None,
                                            push_on_exchange=True):
        self.exchange_manager.trader.allow_artificial_orders = False
        return await self.create_order(stop_price, current_price, size, side, trading_enums.TraderOrderType.STOP_LOSS,
                                       symbol=symbol, push_on_exchange=push_on_exchange)

    async def create_market_order(self, current_price, size, side, symbol=None,
                                  push_on_exchange=True):
        order_type = trading_enums.TraderOrderType.BUY_MARKET \
            if side is trading_enums.TradeOrderSide.BUY else trading_enums.TraderOrderType.SELL_MARKET
        return await self.create_order(None, current_price, size, side, order_type,
                                       symbol=symbol, push_on_exchange=push_on_exchange)

    async def create_order(self, price, current_price, size, side, order_type,
                           symbol=None, push_on_exchange=True):
        current_order = personal_data.create_order_instance(
            self.exchange_manager.trader,
            order_type=order_type,
            symbol=symbol or self.SYMBOL,
            current_price=current_price,
            quantity=size,
            price=price,
            side=side,
        )
        if push_on_exchange:
            current_order = await self._create_order_on_exchange(current_order)
        if current_order is None:
            raise AssertionError("Error when creating order")
        return current_order

    async def _create_order_on_exchange(self, order, params=None):
        created_order = await self.exchange_manager.trader.create_order(order, params=params, wait_for_creation=False)
        if created_order.status is trading_enums.OrderStatus.PENDING_CREATION:
            await self.wait_for_open(created_order)
            return await self.get_order(created_order.order_id)
        return created_order

    def get_order_size(self, portfolio, price, symbol=None, order_size=None):
        order_size = order_size or self.ORDER_SIZE
        currency_quantity = portfolio[self.SETTLEMENT_CURRENCY][self.PORTFOLIO_TYPE_FOR_SIZE] \
            * decimal.Decimal(order_size) / trading_constants.ONE_HUNDRED
        symbol = symbols.parse_symbol(symbol or self.SYMBOL)
        if symbol.is_inverse():
            order_quantity = currency_quantity * price
        else:
            order_quantity = currency_quantity / price
        return personal_data.decimal_adapt_quantity(
            self.exchange_manager.exchange.get_market_status(str(symbol)),
            order_quantity
        )

    def get_sell_size_from_buy_order(self, buy_order):
        sell_size = buy_order.origin_quantity
        if buy_order.fee and buy_order.fee[trading_enums.FeePropertyColumns.CURRENCY.value] == self.ORDER_CURRENCY:
            sell_size = sell_size - buy_order.fee[trading_enums.FeePropertyColumns.COST.value]
        return personal_data.decimal_adapt_quantity(
            self.exchange_manager.exchange.get_market_status(str(buy_order.symbol)),
            sell_size
        )

    def get_order_price(self, price, is_above_price, symbol=None, price_diff=None):
        price_diff = price_diff or self.ORDER_PRICE_DIFF
        multiplier = 1 + price_diff / 100 if is_above_price else 1 - price_diff / 100
        return personal_data.decimal_adapt_price(
            self.exchange_manager.exchange.get_market_status(symbol or self.SYMBOL),
            price * (decimal.Decimal(str(multiplier)))
        )

    async def get_open_orders(self, symbol=None):
        orders = await self.exchange_manager.exchange.get_open_orders(symbol or self.SYMBOL)
        self.check_duplicate(orders)
        return orders

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

    def check_created_stop_order(self, order, price, size, side):
        self._check_order(order, size, side)
        assert order.origin_price == price
        assert order.side is side
        expected_type = personal_data.StopLossOrder
        assert isinstance(order, expected_type)

    def check_portfolio_changed(self, previous_portfolio, updated_portfolio, has_increased, symbol=None):
        previous_free_quantity = previous_portfolio[symbol or self.SETTLEMENT_CURRENCY][
            trading_constants.CONFIG_PORTFOLIO_FREE]
        updated_free_quantity = updated_portfolio[symbol or self.SETTLEMENT_CURRENCY][
            trading_constants.CONFIG_PORTFOLIO_FREE]
        if has_increased:
            assert updated_free_quantity > previous_free_quantity
        else:
            assert updated_free_quantity < previous_free_quantity

    def _check_order(self, order, size, side):
        if self.CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES:
            # actual origin_quantity may vary due to quantity conversion for market orders
            assert size * decimal.Decimal("0.8") <= order.origin_quantity <= size * decimal.Decimal("1.2")
        else:
            assert order.origin_quantity == size
        assert order.side is side
        assert order.is_open()

    async def wait_for_fill(self, order):
        def parse_is_filled(raw_order):
            return personal_data.parse_order_status(raw_order) in {trading_enums.OrderStatus.FILLED,
                                                                   trading_enums.OrderStatus.CLOSED}
        await self._get_order_until(order, parse_is_filled, self.MARKET_FILL_TIMEOUT)

    def parse_order_is_not_pending(self, raw_order):
        return personal_data.parse_order_status(raw_order) not in (trading_enums.OrderStatus.UNKNOWN, None)

    async def wait_for_open(self, order):
        await self._get_order_until(order, self.parse_order_is_not_pending, self.OPEN_TIMEOUT)

    async def wait_for_cancel(self, order):
        return personal_data.create_order_instance_from_raw(
            self.exchange_manager.trader,
            await self._get_order_until(order, personal_data.parse_is_cancelled, self.CANCEL_TIMEOUT)
        )

    async def wait_for_edit(self, order, edited_quantity):
        def is_edited(row_order):
            return decimal.Decimal(str(row_order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value])) \
                   == edited_quantity
        await self._get_order_until(order, is_edited, self.EDIT_TIMEOUT)

    async def _get_order_until(self, order, validation_func, timeout):
        t0 = time.time()
        while time.time() - t0 < timeout:
            raw_order = await self.exchange_manager.exchange.get_order(order.order_id, order.symbol)
            if raw_order and validation_func(raw_order):
                return raw_order
        raise TimeoutError(f"Order not filled within {timeout}s: {order}")

    async def order_in_open_orders(self, previous_open_orders, order):
        open_orders = await self.get_open_orders()
        assert len(open_orders) == len(previous_open_orders) + 1
        for open_order in open_orders:
            if open_order[trading_enums.ExchangeConstantsOrderColumns.ID.value] == order.order_id:
                return True
        return False

    async def get_similar_orders_in_open_orders(self, previous_open_orders, orders):
        if not isinstance(orders, list):
            orders = [orders]
        found_orders = []
        open_orders = await self.get_open_orders()
        assert len(open_orders) == len(previous_open_orders) + len(orders)
        for order in orders:
            for open_order in open_orders:
                fetched_order = personal_data_orders.order_factory.create_order_instance_from_raw(
                    self.exchange_manager.trader,
                    open_order
                )
                if personal_data.is_associated_pending_order(order, fetched_order):
                    found_orders.append(fetched_order)
                    break
        if len(found_orders) == len(orders):
            return found_orders
        raise AssertionError(f"Can't find any order similar to {orders}. Found: {found_orders}")

    async def order_not_in_open_orders(self, previous_open_orders, order):
        open_orders = await self.get_open_orders()
        assert len(open_orders) == len(previous_open_orders)
        for open_order in open_orders:
            if open_order[trading_enums.ExchangeConstantsOrderColumns.ID.value] == order.order_id:
                return False
        return True

    async def cancel_order(self, order):
        cancelled_order = order
        if not await self.exchange_manager.trader.cancel_order(order, wait_for_cancelling=False):
            raise AssertionError("cancel_order returned False")
        if order.status is trading_enums.OrderStatus.PENDING_CANCEL:
            cancelled_order = await self.wait_for_cancel(order)
        assert cancelled_order.status is trading_enums.OrderStatus.CANCELED
        if cancelled_order.state is not None:
            assert cancelled_order.is_cancelled()
        return order

    def get_config(self):
        return {
            constants.CONFIG_EXCHANGES: {
                self.EXCHANGE_NAME: {
                    constants.CONFIG_EXCHANGE_TYPE: self.EXCHANGE_TYPE
                }
            }
        }
