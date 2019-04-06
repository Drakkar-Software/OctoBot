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

from tools.logging.logging_util import get_logger
from asyncio import Lock

from config import CONFIG_SIMULATOR, CONFIG_STARTING_PORTFOLIO, CONFIG_PORTFOLIO_FREE, CONFIG_PORTFOLIO_TOTAL, \
    TradeOrderSide, TraderOrderType, SIMULATOR_CURRENT_PORTFOLIO, CURRENT_PORTFOLIO_STRING
from trading.trader.order import OrderConstants
from tools.initializable import Initializable
from backtesting import backtesting_enabled

""" The Portfolio class manage an exchange portfolio
This will begin by loading current exchange portfolio (by pulling user data)
In case of simulation this will load the CONFIG_STARTING_PORTFOLIO
This class also manage the availability of each currency in the portfolio:
- When an order is created it will subtract the quantity of the total
- When an order is filled or canceled restore the availability with the real quantity """


class Portfolio(Initializable):
    AVAILABLE = "available"
    TOTAL = "total"

    def __init__(self, config, trader):
        super().__init__()
        self.config = config
        self.trader = trader
        self.is_simulated = trader.simulate
        self.is_enabled = trader.enable
        self.portfolio = {}
        exchange = self.trader.get_exchange().get_name()
        self.logger = get_logger(f"{self.__class__.__name__}{'Simulator' if self.is_simulated else ''}[{exchange}]")
        self.lock = Lock()

    async def initialize_impl(self):
        await self._load_portfolio()

    # syntax: "async with xxx.get_lock():"
    # TODO find better way to handle async lock: reuse disposable design pattern ?
    def get_lock(self):
        return self.lock

    # Load exchange portfolio / simulated portfolio from config
    async def _load_portfolio(self):
        if self.is_enabled:
            if self.is_simulated:
                self.set_starting_simulated_portfolio()
            else:
                await self.update_portfolio_balance()
            self.logger.info(f"{CURRENT_PORTFOLIO_STRING} {self.portfolio}")

    def set_starting_simulated_portfolio(self):
        # should only be called in trading simulation
        if self.trader.get_loaded_previous_state():
            # load portfolio from previous execution
            portfolio_amount_dict = self.trader.get_previous_state_manager().get_previous_state(
                self.trader.get_exchange(),
                SIMULATOR_CURRENT_PORTFOLIO
            )
        else:
            # load new portfolio from config settings
            portfolio_amount_dict = self.config[CONFIG_SIMULATOR][CONFIG_STARTING_PORTFOLIO]
        try:
            self.portfolio = self.get_portfolio_from_amount_dict(portfolio_amount_dict)
        except Exception as e:
            self.logger.warning(f"Error when loading trading history, will reset history. ({e})")
            self.logger.exception(e)
            self.trader.get_previous_state_manager.reset_trading_history()
            self.portfolio = self.get_portfolio_from_amount_dict(
                self.config[CONFIG_SIMULATOR][CONFIG_STARTING_PORTFOLIO])

    @staticmethod
    def get_portfolio_from_amount_dict(amount_dict):
        if not all(isinstance(i, (int, float)) for i in amount_dict.values()):
            raise RuntimeError("Portfolio has to be initialized using numbers")
        return {currency: {Portfolio.AVAILABLE: total, Portfolio.TOTAL: total}
                for currency, total in amount_dict.items()}

    async def update_portfolio_balance(self):
        if not self.is_simulated and self.is_enabled:
            balance = await self.trader.get_exchange().get_balance()

            self.portfolio = {currency: {Portfolio.AVAILABLE: balance[currency][CONFIG_PORTFOLIO_FREE],
                                         Portfolio.TOTAL: balance[currency][CONFIG_PORTFOLIO_TOTAL]}
                              for currency in balance}

    def get_portfolio(self):
        return self.portfolio

    @staticmethod
    def get_currency_from_given_portfolio(portfolio, currency, portfolio_type=AVAILABLE):
        if currency in portfolio:
            return portfolio[currency][portfolio_type]
        else:
            portfolio[currency] = {
                Portfolio.AVAILABLE: 0,
                Portfolio.TOTAL: 0
            }
            return portfolio[currency][portfolio_type]

    # Get specified currency quantity in the portfolio
    def get_currency_portfolio(self, currency, portfolio_type=AVAILABLE):
        return self.get_currency_from_given_portfolio(self.portfolio, currency, portfolio_type)

    # Set new currency quantity in the portfolio
    def _update_portfolio_data(self, currency, value, total=True, available=False):
        if currency in self.portfolio:
            if total:
                self.portfolio[currency][Portfolio.TOTAL] += value
            if available:
                self.portfolio[currency][Portfolio.AVAILABLE] += value
        else:
            self.portfolio[currency] = {Portfolio.AVAILABLE: value, Portfolio.TOTAL: value}

    """ update_portfolio performs the update of the total / available quantity of a currency
    It is called only when an order is filled to update the real quantity of the currency to be set in "total" field
    Returns get_profitability() return
    """

    async def update_portfolio(self, order):
        if self.is_simulated:
            # stop losses and take profits aren't using available portfolio
            if not self._check_available_should_update(order):
                self._update_portfolio_available(order)

            currency, market = order.get_currency_and_market()

            # update currency
            if order.get_side() == TradeOrderSide.BUY:
                new_quantity = order.get_filled_quantity() - order.get_total_fees(currency)
                self._update_portfolio_data(currency, new_quantity, True, True)
            else:
                new_quantity = -order.get_filled_quantity()
                self._update_portfolio_data(currency, new_quantity, True, False)

            # update market
            if order.get_side() == TradeOrderSide.BUY:
                new_quantity = -(order.get_filled_quantity() * order.get_filled_price())
                self._update_portfolio_data(market, new_quantity, True, False)
            else:
                new_quantity = (order.get_filled_quantity() * order.get_filled_price()) - order.get_total_fees(market)
                self._update_portfolio_data(market, new_quantity, True, True)

            # Only for log purpose
            if order.get_side() == TradeOrderSide.BUY:
                currency_portfolio_num = order.get_filled_quantity() - order.get_total_fees(currency)
                market_portfolio_num = -order.get_filled_quantity() * order.get_filled_price()
            else:
                currency_portfolio_num = -order.get_filled_quantity()
                market_portfolio_num = \
                    order.get_filled_quantity() * order.get_filled_price() - order.get_total_fees(market)

            self.logger.info(f"Portfolio updated | {currency} {currency_portfolio_num} | {market} "
                             f"{market_portfolio_num} | {CURRENT_PORTFOLIO_STRING} {self.portfolio}")
        else:
            await self.update_portfolio_balance()
            self.logger.info(f"Portfolio updated | {CURRENT_PORTFOLIO_STRING} {self.portfolio}")

    """ update_portfolio_available performs the availability update of the concerned currency in the current portfolio
    It is called when an order is filled, created or canceled to update the "available" filed of the portfolio
    is_new_order is True when portfolio needs an update after a new order and False when portfolio needs a rollback 
    after an order is cancelled
    """

    def update_portfolio_available(self, order, is_new_order=False):
        if self._check_available_should_update(order):
            self._update_portfolio_available(order, 1 if is_new_order else -1)

    # Check if the order has impact on availability
    @staticmethod
    def _check_available_should_update(order):
        # stop losses and take profits aren't using available portfolio
        return order.__class__ not in [OrderConstants.TraderOrderTypeClasses[TraderOrderType.TAKE_PROFIT],
                                       OrderConstants.TraderOrderTypeClasses[TraderOrderType.TAKE_PROFIT_LIMIT],
                                       OrderConstants.TraderOrderTypeClasses[TraderOrderType.STOP_LOSS],
                                       OrderConstants.TraderOrderTypeClasses[TraderOrderType.STOP_LOSS_LIMIT]]

    # Realise portfolio availability update
    def _update_portfolio_available(self, order, factor=1):
        currency, market = order.get_currency_and_market()

        # when buy order
        if order.get_side() == TradeOrderSide.BUY:
            new_quantity = - order.get_origin_quantity() * order.get_origin_price() * factor
            self._update_portfolio_data(market, new_quantity, False, True)

        # when sell order
        else:
            new_quantity = - order.get_origin_quantity() * factor
            self._update_portfolio_data(currency, new_quantity, False, True)

    # Resets available amount with total amount CAREFUL: if no currency is give, resets all the portfolio !
    def reset_portfolio_available(self, reset_currency=None, reset_quantity=None):
        if not reset_currency:
            self.portfolio.update({currency: {Portfolio.AVAILABLE: self.portfolio[currency][Portfolio.TOTAL],
                                              Portfolio.TOTAL: self.portfolio[currency][Portfolio.TOTAL]}
                                   for currency in self.portfolio})
        else:
            if reset_currency in self.portfolio:
                if reset_quantity is None:
                    self.portfolio[reset_currency][Portfolio.AVAILABLE] = \
                        self.portfolio[reset_currency][Portfolio.TOTAL]
                else:
                    self.portfolio[reset_currency][Portfolio.AVAILABLE] += reset_quantity
