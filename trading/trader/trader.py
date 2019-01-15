#  Drakkar-Software OctoBot
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
from tools.logging.logging_util import get_logger

from backtesting.backtesting import Backtesting
from config import CONFIG_ENABLED_OPTION, CONFIG_TRADER, CONFIG_TRADING, CONFIG_TRADER_RISK, CONFIG_TRADER_RISK_MIN, \
    CONFIG_TRADER_RISK_MAX, OrderStatus, TradeOrderSide, TraderOrderType, REAL_TRADER_STR, TradeOrderType
from tools.pretty_printer import PrettyPrinter
from trading.trader.order import OrderConstants, Order
from trading.trader.order_notifier import OrderNotifier
from trading.trader.orders_manager import OrdersManager
from trading.trader.portfolio import Portfolio
from trading.trader.trade import Trade
from trading.trader.trades_manager import TradesManager
from tools.initializable import Initializable


class Trader(Initializable):

    def __init__(self, config, exchange, order_refresh_time=None):
        super().__init__()
        self.exchange = exchange
        self.config = config
        self.risk = None
        self.set_risk(self.config[CONFIG_TRADING][CONFIG_TRADER_RISK])

        # logging
        self.trader_type_str = REAL_TRADER_STR
        self.logger = get_logger(self.__class__.__name__)

        if not hasattr(self, 'simulate'):
            self.simulate = False

        self.enable = self.enabled(self.config)

        self.portfolio = Portfolio(self.config, self)

        self.trades_manager = TradesManager(config, self)

        self.order_manager = OrdersManager(config, self)

        self.exchange.get_exchange_manager().register_trader(self)

        if order_refresh_time is not None:
            self.order_manager.set_order_refresh_time(order_refresh_time)

    async def initialize_impl(self):
        await self.portfolio.initialize()
        await self.trades_manager.initialize()

    async def launch(self):
        if self.enable:
            if not self.simulate:
                await self.update_open_orders()
                # self.update_close_orders()

                # can current orders received: start using websocket for orders if available
                self.exchange.get_exchange_personal_data().init_orders()

            await self.start_order_manager()
            self.logger.debug(f"Enabled on {self.exchange.get_name()}")
        else:
            self.logger.debug(f"Disabled on {self.exchange.get_name()}")

    @staticmethod
    def enabled(config):
        return config[CONFIG_TRADER][CONFIG_ENABLED_OPTION]

    def is_enabled(self):
        return self.enable

    def set_enabled(self, enable):
        self.enable = enable

    def get_risk(self):
        return self.risk

    def set_risk(self, risk):
        if risk < CONFIG_TRADER_RISK_MIN:
            self.risk = CONFIG_TRADER_RISK_MIN
        elif risk > CONFIG_TRADER_RISK_MAX:
            self.risk = CONFIG_TRADER_RISK_MAX
        else:
            self.risk = risk

    def get_exchange(self):
        return self.exchange

    def get_portfolio(self):
        return self.portfolio

    def get_order_portfolio(self, order):
        return order.get_linked_portfolio() if order.get_linked_portfolio() is not None else self.portfolio

    def create_order_instance(self, order_type, symbol, current_price, quantity,
                              price=None,
                              stop_price=None,
                              linked_to=None,
                              status=None,
                              order_id=None,
                              quantity_filled=None,
                              timestamp=None,
                              linked_portfolio=None):

        # create new order instance
        order_class = OrderConstants.TraderOrderTypeClasses[order_type]
        order = order_class(self)

        # manage order notifier
        if linked_to is None:
            order_notifier = OrderNotifier(self.config, order)
        else:
            order_notifier = linked_to.get_order_notifier()

        order.new(order_type=order_type,
                  symbol=symbol,
                  current_price=current_price,
                  quantity=quantity,
                  price=price,
                  stop_price=stop_price,
                  order_notifier=order_notifier,
                  order_id=order_id,
                  status=status,
                  quantity_filled=quantity_filled,
                  timestamp=timestamp,
                  linked_to=linked_to,
                  linked_portfolio=linked_portfolio)

        return order

    async def create_order(self, order, portfolio, loaded=False):
        linked_to = None

        new_order = order
        is_to_keep = True
        is_already_in_history = False

        # if this order is linked to another (ex : a sell limit order with a stop loss order)
        if new_order.linked_to is not None:
            new_order.linked_to.add_linked_order(new_order)
            linked_to = new_order.linked_to

        if not loaded:
            new_order = await self._create_not_loaded_order(order, new_order, portfolio)
            title = "Order creation"
        else:
            new_order.set_is_from_this_octobot(False)
            title = "Order loaded"
            is_already_in_history = self.trades_manager.is_in_history(new_order)
            if is_already_in_history or \
                    (new_order.get_status() != OrderStatus.OPEN and
                     new_order.get_status() != OrderStatus.PARTIALLY_FILLED):
                is_to_keep = False

        self.logger.info(f"{title} : {new_order.get_string_info()} "
                         f"{'' if is_to_keep else ': will be archived in trades history if not already'}")

        if is_to_keep:
            # notify order manager of a new open order
            self.order_manager.add_order_to_list(new_order)
        elif not is_already_in_history:
            self.trades_manager.add_new_trade_in_history(Trade(self.exchange, new_order))

        # if this order is linked to another
        if linked_to is not None:
            new_order.add_linked_order(linked_to)

        return new_order

    async def create_artificial_order(self, order_type, symbol, current_price, quantity, price, linked_portfolio):
        market_sell = self.create_order_instance(order_type=order_type,
                                                 symbol=symbol,
                                                 current_price=current_price,
                                                 quantity=quantity,
                                                 price=price,
                                                 linked_portfolio=linked_portfolio)
        async with self.get_portfolio().get_lock():
            await self.create_order(market_sell, self.get_portfolio())

    async def _create_not_loaded_order(self, order, new_order, portfolio) -> Order:
        if not self.simulate and not self.check_if_self_managed(new_order.get_order_type()):
            created_order = await self.exchange.create_order(new_order.get_order_type(),
                                                             new_order.get_order_symbol(),
                                                             new_order.get_origin_quantity(),
                                                             new_order.get_origin_price(),
                                                             new_order.origin_stop_price)

            # get real order from exchange
            new_order = self.parse_exchange_order_to_order_instance(created_order)

            # rebind order notifier and linked portfolio to new order instance
            new_order.order_notifier = order.get_order_notifier()
            new_order.get_order_notifier().set_order(new_order)
            new_order.linked_portfolio = portfolio

        # update the availability of the currency in the portfolio
        portfolio.update_portfolio_available(new_order, is_new_order=True)

        return new_order

    async def cancel_order(self, order):
        if not order.is_cancelled() and not order.is_filled():
            async with order.get_lock():
                odr = order
                await odr.cancel_order()
                self.logger.info(f"{odr.get_order_symbol()} {odr.get_name()} at {odr.get_origin_price()}"
                                 f" (ID : {odr.get_id()}) cancelled on {self.get_exchange().get_name()}")

                self.order_manager.remove_order_from_list(order)

    # Should be called only if we want to cancel all symbol open orders (no filled)
    async def cancel_open_orders(self, symbol, cancel_loaded_orders=True):
        # use a copy of the list (not the reference)
        for order in copy.copy(self.get_open_orders()):
            if order.get_order_symbol() == symbol and order.get_status() is not OrderStatus.CANCELED:
                if cancel_loaded_orders or order.get_is_from_this_octobot():
                    await self.notify_order_close(order, True)

    async def cancel_all_open_orders(self):
        # use a copy of the list (not the reference)
        for order in copy.copy(self.get_open_orders()):
            if order.get_status() is not OrderStatus.CANCELED:
                await self.notify_order_close(order, True)

    async def notify_order_cancel(self, order):
        # update portfolio with ended order
        async with self.get_order_portfolio(order).get_lock():
            self.get_order_portfolio(order).update_portfolio_available(order, is_new_order=False)

    async def notify_order_close(self, order, cancel=False, cancel_linked_only=False):
        # Cancel linked orders
        for linked_order in order.get_linked_orders():
            await self.cancel_order(linked_order)

        # If need to cancel the order call the method and no need to update the portfolio (only availability)
        if cancel:
            order_closed = None
            orders_canceled = order.get_linked_orders() + [order]

            await self.cancel_order(order)
            _, profitability_percent, profitability_diff = self.get_trades_manager().get_profitability_without_update()

        elif cancel_linked_only:
            order_closed = None
            orders_canceled = order.get_linked_orders()

            _, profitability_percent, profitability_diff = self.get_trades_manager().get_profitability_without_update()

        else:
            order_closed = order
            orders_canceled = order.get_linked_orders()

            # update portfolio with ended order
            async with self.get_order_portfolio(order).get_lock():
                await self.get_order_portfolio(order).update_portfolio(order)

            profitability, profitability_percent, profitability_diff, _, _ = \
                await self.get_trades_manager().get_profitability()

            # debug purpose
            profitability_str = PrettyPrinter.portfolio_profitability_pretty_print(profitability,
                                                                                   profitability_percent,
                                                                                   self.get_trades_manager().
                                                                                   get_reference())

            self.logger.debug(f"Current portfolio profitability : {profitability_str}")

            # add to trade history
            self.trades_manager.add_new_trade_in_history(Trade(self.exchange, order))

            # remove order to open_orders
            self.order_manager.remove_order_from_list(order)

        profitability_activated = order_closed is not None

        # update current order list with exchange
        if not self.simulate:
            await self.update_open_orders(order.get_order_symbol())

        # notification
        await order.get_order_notifier().end(order_closed,
                                             orders_canceled,
                                             order.get_profitability(),
                                             profitability_percent,
                                             profitability_diff,
                                             profitability_activated)

    def get_open_orders(self):
        return self.order_manager.get_open_orders()

    def update_close_orders(self):
        for symbol in self.exchange.get_exchange_manager().get_traded_pairs():
            for close_order in self.exchange.get_closed_orders(symbol):
                self.parse_exchange_order_to_trade_instance(close_order, Order(self))

    async def update_open_orders(self, symbol=None):
        if symbol:
            symbols = [symbol]
        else:
            symbols = self.exchange.get_exchange_manager().get_traded_pairs()

        # get orders from exchange for the specified symbols
        for symbol_traded in symbols:
            orders = await self.exchange.get_open_orders(symbol=symbol_traded, force_rest=True)
            for open_order in orders:
                order = self.parse_exchange_order_to_order_instance(open_order)
                async with self.portfolio.get_lock():
                    await self.create_order(order, self.portfolio, True)

    async def force_refresh_portfolio(self, portfolio=None):
        if not self.simulate:
            self.logger.info(f"Triggered forced {self.exchange.get_name()} trader portfolio refresh")
            if portfolio:
                await portfolio.update_portfolio_balance()
            else:
                async with self.portfolio.get_lock():
                    await self.portfolio.update_portfolio_balance()

    async def force_refresh_orders(self, portfolio=None):
        # useless in simulation mode
        if not self.simulate:
            self.logger.info(f"Triggered forced {self.exchange.get_name()} trader orders refresh")
            symbols = self.exchange.get_exchange_manager().get_traded_pairs()

            # get orders from exchange for the specified symbols
            for symbol_traded in symbols:

                orders = await self.exchange.get_open_orders(symbol=symbol_traded, force_rest=True)
                for open_order in orders:
                    # do something only if order not already in list
                    if not self.order_manager.has_order_id_in_list(open_order["id"]):
                        order = self.parse_exchange_order_to_order_instance(open_order)
                        if portfolio:
                            await self.create_order(order, portfolio, True)
                        else:
                            async with self.portfolio.get_lock():
                                await self.create_order(order, self.portfolio, True)

    def parse_exchange_order_to_order_instance(self, order):
        return self.create_order_instance(order_type=self.parse_order_type(order),
                                          symbol=order["symbol"],
                                          current_price=0,
                                          quantity=order["amount"],
                                          stop_price=None,
                                          linked_to=None,
                                          quantity_filled=order["filled"],
                                          order_id=order["id"],
                                          status=self.parse_status(order),
                                          price=order["price"],
                                          timestamp=order["timestamp"])

    @staticmethod
    def update_order_with_exchange_order(exchange_order, order):
        order.status = Trader.parse_status(exchange_order)
        order.filled_quantity = exchange_order["filled"]
        order.filled_price = exchange_order["price"]
        order.fee = exchange_order["fee"]
        order.executed_time = order.trader.exchange.get_uniform_timestamp(exchange_order["timestamp"])  # to confirm

    def parse_exchange_order_to_trade_instance(self, exchange_order, order):
        self.update_order_with_exchange_order(exchange_order, order)

    @staticmethod
    def parse_status(order):
        return OrderStatus(order["status"])

    @staticmethod
    def parse_order_type(order):
        side = TradeOrderSide(order["side"])
        order_type = TradeOrderType(order["type"])
        if side == TradeOrderSide.BUY:
            if order_type == TradeOrderType.LIMIT:
                return TraderOrderType.BUY_LIMIT
            elif order_type == TradeOrderType.MARKET:
                return TraderOrderType.BUY_MARKET
        elif side == TradeOrderSide.SELL:
            if order_type == TradeOrderType.LIMIT:
                return TraderOrderType.SELL_LIMIT
            elif order_type == TradeOrderType.MARKET:
                return TraderOrderType.SELL_MARKET

    def get_order_manager(self):
        return self.order_manager

    def get_trades_manager(self):
        return self.trades_manager

    def stop_order_manager(self):
        self.order_manager.stop()

    async def start_order_manager(self):
        if not Backtesting.enabled(self.config):
            await self.order_manager.poll_update()

    def get_simulate(self):
        return self.simulate

    @staticmethod
    def check_if_self_managed(order_type):
        # stop losses and take profits are self managed by the bot
        if order_type in [TraderOrderType.TAKE_PROFIT,
                          TraderOrderType.TAKE_PROFIT_LIMIT,
                          TraderOrderType.STOP_LOSS,
                          TraderOrderType.STOP_LOSS_LIMIT]:
            return True
        return False
