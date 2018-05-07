import logging

from config.cst import CONFIG_TRADER, CONFIG_TRADER_REFERENCE_MARKET, DEFAULT_REFERENCE_MARKET
from trading.trader.portfolio import Portfolio, ExchangeConstantsTickersColumns

""" TradesManager will store all trades performed by the exchange trader
Another feature of TradesManager is the profitability calculation
by subtracting portfolio_current_value and portfolio_origin_value """


class TradesManager:
    def __init__(self, config, trader):
        self.config = config
        self.trader = trader
        self.portfolio = trader.get_portfolio()
        self.exchange = trader.get_exchange()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.trade_history = []
        self.profitability = 0
        self.profitability_percent = 0
        self.profitability_diff = 0

        self.currencies_prices = None
        self.origin_portfolio = None
        self.last_portfolio = None

        self.portfolio_origin_value = 0
        self.portfolio_current_value = 0
        self.trades_value = 0

        self.reference_market = TradesManager.get_reference_market(self.config)

        self._get_portfolio_origin_value()

    @staticmethod
    def get_reference_market(config):
        # The reference market is the currency unit of the calculated quantity value
        if CONFIG_TRADER_REFERENCE_MARKET in config[CONFIG_TRADER]:
            return config[CONFIG_TRADER][CONFIG_TRADER_REFERENCE_MARKET]
        else:
            return DEFAULT_REFERENCE_MARKET

    def get_reference(self):
        return self.reference_market

    def add_new_trade_in_history(self, trade):
        if trade not in self.trade_history:
            self.trade_history.append(trade)

    """ get currencies prices update currencies data by polling tickers from exchange
    and set currencies_prices attribute
    """

    def _update_currencies_prices(self):
        self.currencies_prices = self.exchange.get_all_currencies_price_ticker()

    """ Get profitability calls get_currencies_prices to update required data
    Then calls get_portfolio_current_value to set the current value of portfolio_current_value attribute
    Returns the profitability, the profitability percentage and the difference with the last portfolio profitability
    """

    def get_profitability(self):
        self.profitability_diff = self.profitability_percent
        self.profitability = 0
        self.profitability_percent = 0

        try:
            self._update_currencies_prices()
            self._update_portfolio_current_value()
            self.profitability = self.portfolio_current_value - self.portfolio_origin_value

            if self.portfolio_origin_value > 0:
                self.profitability_percent = (100 * self.portfolio_current_value / self.portfolio_origin_value) - 100
            else:
                self.profitability_percent = 0

            # calculate difference with the last current portfolio
            self.profitability_diff = self.profitability_percent - self.profitability_diff
        except Exception as e:
            self.logger.error(str(e))

        return self.get_profitability_without_update()

    def get_profitability_without_update(self):
        return self.profitability, self.profitability_percent, self.profitability_diff

    def get_portfolio_current_value(self):
        return self.portfolio_current_value

    def get_portfolio_origin_value(self):
        return self.portfolio_origin_value

    # Currently unused method
    def get_trades_value(self):
        self.trades_value = 0
        for trade in self.trade_history:
            self.trades_value += self._evaluate_value(trade.get_currency(), trade.get_quantity())
        return self.trades_value

    def get_trade_history(self):
        return self.trade_history

    def _update_portfolio_current_value(self):
        with self.portfolio as pf:
            self.last_portfolio = pf.get_portfolio()
        self.portfolio_current_value = self._evaluate_portfolio_value(self.last_portfolio)

    def _get_portfolio_origin_value(self):
        self._update_currencies_prices()
        with self.portfolio as pf:
            self.origin_portfolio = pf.get_portfolio()
        self.portfolio_origin_value += self._evaluate_portfolio_value(self.origin_portfolio)

    """ try_get_value_of_currency will try to obtain the current value of the currency quantity in the reference currency
    It will try to create the symbol that fit with the exchange logic
    Returns the value found of this currency quantity, if not found returns 0     
    """
    # TODO : use ccxt method
    def _try_get_value_of_currency(self, currency, quantity):
        symbol = self.exchange.merge_currencies(currency, self.reference_market)
        symbol_inverted = self.exchange.merge_currencies(self.reference_market, currency)
        if symbol in self.currencies_prices:
            return self.currencies_prices[symbol][ExchangeConstantsTickersColumns.LAST.value] * quantity
        elif symbol_inverted in self.currencies_prices:
            return quantity / self.currencies_prices[symbol_inverted][ExchangeConstantsTickersColumns.LAST.value]
        else:
            # TODO : manage if currency/market doesn't exist
            return 0

    """ evaluate_portfolio_value performs evaluate_value with a portfolio configuration
    Returns the calculated quantity value in reference (attribute) currency
    """

    def _evaluate_portfolio_value(self, portfolio):
        value = 0
        for currency in portfolio:
            value += self._evaluate_value(currency, portfolio[currency][Portfolio.TOTAL])
        return value

    # Evaluate value returns the currency quantity value in the reference (attribute) currency
    def _evaluate_value(self, currency, quantity):
        # easy case --> the current currency is the reference currency
        if currency == self.reference_market:
            return quantity
        else:
            return self._try_get_value_of_currency(currency, quantity)
