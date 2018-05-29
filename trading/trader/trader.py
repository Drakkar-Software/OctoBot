import logging

from config.cst import CONFIG_ENABLED_OPTION, CONFIG_TRADER, CONFIG_TRADER_RISK, CONFIG_TRADER_RISK_MIN, \
    CONFIG_TRADER_RISK_MAX, OrderStatus, TradeOrderSide, TraderOrderType
from tools.pretty_printer import PrettyPrinter
from trading.trader.order import OrderConstants
from trading.trader.order_notifier import OrderNotifier
from trading.trader.orders_manager import OrdersManager
from trading.trader.portfolio import Portfolio
from trading.trader.trade import Trade
from trading.trader.trades_manager import TradesManager


class Trader:
    def __init__(self, config, exchange, order_refresh_time=None):
        self.exchange = exchange
        self.config = config
        self.risk = None
        self.set_risk(self.config[CONFIG_TRADER][CONFIG_TRADER_RISK])
        self.logger = logging.getLogger(self.__class__.__name__)

        if not hasattr(self, 'simulate'):
            self.simulate = False

        self.enable = self.enabled(self.config)

        self.portfolio = Portfolio(self.config, self)

        self.trades_manager = TradesManager(config, self)

        self.order_manager = OrdersManager(config, self)

        if order_refresh_time is not None:
            self.order_manager.set_order_refresh_time(order_refresh_time)

        if self.enable:
            if not self.simulate:
                self.update_open_orders()
                # self.update_close_orders()

                # can current orders received: start using websocket for orders if available
                self.exchange.set_orders_are_initialized(True)

            self.order_manager.start()
            self.logger.debug("Enabled on {0}".format(self.exchange.get_name()))
        else:
            self.logger.debug("Disabled on {0}".format(self.exchange.get_name()))

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

    def create_order_instance(self, order_type, symbol, current_price, quantity,
                              price=None,
                              stop_price=None,
                              linked_to=None,
                              status=None,
                              order_id=None,
                              quantity_filled=None,
                              timestamp=None):

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
                  linked_to=linked_to)

        return order

    def create_order(self, order, portfolio, loaded=False):
        if not loaded:
            if not self.simulate and not self.check_if_self_managed(order.get_order_type()):
                new_order = self.exchange.create_order(order.get_order_type(),
                                                       order.get_order_symbol(),
                                                       order.get_origin_quantity(),
                                                       order.get_origin_price(),
                                                       order.origin_stop_price)
                order = self.parse_exchange_order_to_order_instance(new_order)

        self.logger.info("Order creation : {0} | {1} | Price : {2} | Quantity : {3}".format(order.get_order_symbol(),
                                                                                            order.get_order_type(),
                                                                                            order.get_origin_price(),
                                                                                            order.get_origin_quantity()))

        # update the availability of the currency in the portfolio
        portfolio.update_portfolio_available(order, is_new_order=True)

        # notify order manager of a new open order
        self.order_manager.add_order_to_list(order)

        # if this order is linked to another (ex : a sell limit order with a stop loss order)
        if order.linked_to is not None:
            order.linked_to.add_linked_order(order)
            order.add_linked_order(order.linked_to)

        return order

    def cancel_order(self, order):
        with order as odr:
            odr.cancel_order()
            self.logger.info("{0} {1} at {2} (ID : {3}) cancelled on {4}".format(odr.get_order_symbol(),
                                                                                 odr.get_name(),
                                                                                 odr.get_origin_price(),
                                                                                 odr.get_id(),
                                                                                 self.get_exchange().get_name()))
        self.order_manager.remove_order_from_list(order)

    # Should be called only if we want to cancel all symbol open orders (no filled)
    def cancel_open_orders(self, symbol):
        # use a copy of the list (not the reference)
        for order in list(self.get_open_orders()):
            if order.get_order_symbol() == symbol and order.get_status() is not OrderStatus.CANCELED:
                self.notify_order_close(order, True)

    def cancel_all_open_orders(self):
        # use a copy of the list (not the reference)
        for order in list(self.get_open_orders()):
            if order.get_status() is not OrderStatus.CANCELED:
                self.notify_order_close(order, True)

    def notify_order_cancel(self, order):
        # update portfolio with ended order
        with self.portfolio as pf:
            pf.update_portfolio_available(order, is_new_order=False)

    def notify_order_close(self, order, cancel=False):
        # Cancel linked orders
        for linked_order in order.get_linked_orders():
            self.cancel_order(linked_order)

        # If need to cancel the order call the method and no need to update the portfolio (only availability)
        if cancel:
            order_closed = None
            orders_canceled = order.get_linked_orders() + [order]

            self.cancel_order(order)
            _, profitability_percent, profitability_diff = self.get_trades_manager().get_profitability_without_update()

        else:
            order_closed = order
            orders_canceled = order.get_linked_orders()

            # update portfolio with ended order
            with self.portfolio as pf:
                pf.update_portfolio(order)

            # debug purpose
            profitability, profitability_percent, profitability_diff = self.get_trades_manager().get_profitability()

            self.logger.info("Current portfolio profitability : {0}".format(
                PrettyPrinter.portfolio_profitability_pretty_print(profitability,
                                                                   profitability_percent,
                                                                   self.get_trades_manager().get_reference())))

            # add to trade history
            self.trades_manager.add_new_trade_in_history(Trade(self.exchange, order))

            # remove order to open_orders
            self.order_manager.remove_order_from_list(order)

        profitability_activated = order_closed is not None

        # update current order list with exchange
        if not self.simulate:
            self.update_open_orders()

        # notification
        order.get_order_notifier().end(order_closed,
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
                self.parse_exchange_order_to_trade_instance(close_order)

    def update_open_orders(self):
        for symbol in self.exchange.get_exchange_manager().get_traded_pairs():
            orders = self.exchange.get_open_orders(symbol=symbol)
            for open_order in orders:
                order = self.parse_exchange_order_to_order_instance(open_order)
                with self.portfolio as pf:
                    self.create_order(order, pf, True)

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
        order.executed_time = order.trader.exchange.get_uniform_timestamp(exchange_order["timestamp"])  # to confirm

    def parse_exchange_order_to_trade_instance(self, exchange_order, order):
        self.update_order_with_exchange_order(exchange_order, order)

    @staticmethod
    def parse_status(order):
        return OrderStatus(order["status"])

    @staticmethod
    def parse_order_type(order):
        side = TradeOrderSide(order["side"])
        order_type = order["type"]
        if side == TradeOrderSide.BUY:
            if order_type == "limit":
                return TraderOrderType.BUY_LIMIT
            elif order_type == "market":
                return TraderOrderType.BUY_MARKET
        elif side == TradeOrderSide.SELL:
            if order_type == "limit":
                return TraderOrderType.SELL_LIMIT
            elif order_type == "market":
                return TraderOrderType.SELL_MARKET

    def get_order_manager(self):
        return self.order_manager

    def get_trades_manager(self):
        return self.trades_manager

    def stop_order_manager(self):
        self.order_manager.stop()

    def join_order_manager(self):
        if self.order_manager.isAlive():
            self.order_manager.join()

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
