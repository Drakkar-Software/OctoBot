import logging

from config.cst import *
from trading.trader.order import OrderConstants

""" The Portfolio class manage an exchange portfolio
This will begin by loading current exchange portfolio (by pulling user data)
In case of simulation this will load the CONFIG_STARTING_PORTFOLIO
This class also manage the availability of each currency in the portfolio : 
- When an order is created it will subtract the quantity of the total
- When an order is filled or canceled restore the availability with the real quantity
"""


class Portfolio:
    AVAILABLE = "available"
    TOTAL = "total"

    def __init__(self, config, trader):
        self.config = config
        self.portfolio = {}
        self.load_portfolio()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.trader = trader
        self.exchange = self.trader.get_exchange()

    # Load exchange portfolio / simulated portfolio from config
    def load_portfolio(self):
        if CONFIG_SIMULATOR in self.config and CONFIG_STARTING_PORTFOLIO in self.config[CONFIG_SIMULATOR]:
            for currency, total in self.config[CONFIG_SIMULATOR][CONFIG_STARTING_PORTFOLIO].items():
                self.portfolio[currency] = {Portfolio.AVAILABLE: total, Portfolio.TOTAL: total}

    def get_portfolio(self):
        return self.portfolio

    # Get specified currency quantity in the portfolio
    def get_currency_portfolio(self, currency, portfolio_type=AVAILABLE):
        if currency in self.portfolio:
            return self.portfolio[currency][portfolio_type]
        else:
            self.portfolio[currency] = {
                Portfolio.AVAILABLE: 0,
                Portfolio.TOTAL: 0
            }
            return self.portfolio[currency][portfolio_type]

    # Set new currency quantity in the portfolio
    def update_portfolio_data(self, currency, value, total=True, available=False):
        if currency in self.portfolio:
            if total:
                self.portfolio[currency][Portfolio.TOTAL] += value
            if available:
                self.portfolio[currency][Portfolio.AVAILABLE] += value
        else:
            self.portfolio[currency] = {Portfolio.AVAILABLE: value, Portfolio.TOTAL: value}

    """ update_portfolio performs the update of the total / available quantity of a currency
    It is called only when an order is filled to update the real quantity of the currency to be set in "total" field
    """
    def update_portfolio(self, order):
        currency, market = order.get_currency_and_market()

        # update currency
        if order.get_side() == TradeOrderSide.BUY:
            new_quantity = order.get_filled_quantity() - order.get_currency_total_fees()
        else:
            new_quantity = -(order.get_filled_quantity() - order.get_currency_total_fees())
        self.update_portfolio_data(currency, new_quantity, True, True)

        # update market
        if order.get_side() == TradeOrderSide.BUY:
            new_quantity = -((order.get_filled_quantity() * order.get_filled_price()) - order.get_market_total_fees())
        else:
            new_quantity = (order.get_filled_quantity() * order.get_filled_price()) - order.get_market_total_fees()
        self.update_portfolio_data(market, new_quantity, True, True)

        # Only for log purpose
        if order.get_side() == TradeOrderSide.BUY:
            currency_portfolio_num = order.get_filled_quantity()
            market_portfolio_num = -self.portfolio[market][Portfolio.TOTAL]
        else:
            currency_portfolio_num = -order.get_filled_quantity()
            market_portfolio_num = self.portfolio[market][Portfolio.TOTAL]

        self.logger.info("Portfolio updated | {0} {1} | {2} {3} | Current Portfolio : {4}".format(currency,
                                                                                                  currency_portfolio_num,
                                                                                                  market,
                                                                                                  market_portfolio_num,
                                                                                                  self.portfolio))

        # debug purpose
        profitability, profitability_percent = self.trader.get_trades_manager().get_profitability()
        self.logger.debug("Current portfolio profitability : {0} {1} ({2}%)".format(round(profitability, 2),
                                                                                    self.trader.get_trades_manager().get_reference_market(),
                                                                                    round(profitability_percent, 2)))

    """ update_portfolio_available performs the availability update of the concerned currency in the current portfolio
    It is called when an order is filled, created or canceled to update the "available" filed of the portfolio
    """
    def update_portfolio_available(self, order, is_new_order=True):
        # stop losses and take profits aren't using available portfolio
        if order.__class__ not in [OrderConstants.TraderOrderTypeClasses[TraderOrderType.TAKE_PROFIT],
                                   OrderConstants.TraderOrderTypeClasses[TraderOrderType.TAKE_PROFIT_LIMIT],
                                   OrderConstants.TraderOrderTypeClasses[TraderOrderType.STOP_LOSS],
                                   OrderConstants.TraderOrderTypeClasses[TraderOrderType.STOP_LOSS_LIMIT]]:

            currency, market = order.get_currency_and_market()

            if is_new_order:
                inverse = 1
            else:
                inverse = -1

            if order.get_side() == TradeOrderSide.BUY:
                new_quantity = -order.get_origin_quantity() * order.get_origin_price() * inverse
                self.update_portfolio_data(market, new_quantity, False, True)
            else:
                new_quantity = -order.get_origin_quantity() * inverse
                self.update_portfolio_data(currency, new_quantity, False, True)

            # debug purpose
            self.logger.debug("Portfolio available updated | Current Portfolio : {1}".format(order.get_order_symbol(),
                                                                                             self.portfolio))
