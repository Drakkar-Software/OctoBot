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

from config import CONFIG_PORTFOLIO_FREE, CONFIG_PORTFOLIO_USED, CONFIG_PORTFOLIO_TOTAL
from tools import get_logger
from trading.trader.orders_manager import OrdersManager
from trading.trader.portfolio import Portfolio
from trading.trader.trades_manager import TradesManager


class ExchangePersonalData:
    # note: symbol keys are without /
    def __init__(self, exchange_manager):
        self.logger = get_logger(self.__class__.__name__)
        self.exchange_manager = exchange_manager
        self.exchange = exchange_manager.exchange
        self.config: dict = exchange_manager.config

        self.trader = None
        self.portfolio: Portfolio = None
        self.trades: TradesManager = None
        self.orders: OrdersManager = None

    def initialize(self):
        self.trader = self.exchange_manager.trader
        self.portfolio: Portfolio = Portfolio(self.config, self.trader, self.exchange_manager)
        self.trades: TradesManager = TradesManager(self.config, self.trader, self.exchange_manager)
        self.orders: OrdersManager = OrdersManager(self.config, self.trader, self.exchange_manager)

    async def initialize_impl(self):
        if self.trader.enable:
            try:
                await self.portfolio.initialize()
                await self.trades.initialize()
                await self.orders.initialize()
            except Exception as e:
                self.logger.error(f"Error when initializing portfolio: {e}. "
                                  f"{self.exchange.get_name()} trader disabled.")
                self.logger.exception(e)

    # updates
    def handle_portfolio_update(self, currency, total, available, in_order):
        self.portfolio[currency] = {
            CONFIG_PORTFOLIO_FREE: available,
            CONFIG_PORTFOLIO_USED: in_order,
            CONFIG_PORTFOLIO_TOTAL: total
        }

    def handle_orders_update(self, currency, total, available, in_order):
        self.portfolio[currency] = {
            CONFIG_PORTFOLIO_FREE: available,
            CONFIG_PORTFOLIO_USED: in_order,
            CONFIG_PORTFOLIO_TOTAL: total
        }

    def handle_trades_update(self, currency, total, available, in_order):
        self.portfolio[currency] = {
            CONFIG_PORTFOLIO_FREE: available,
            CONFIG_PORTFOLIO_USED: in_order,
            CONFIG_PORTFOLIO_TOTAL: total
        }

    def get_order_portfolio(self, order):
        return order.linked_portfolio if order.linked_portfolio is not None else self.portfolio
