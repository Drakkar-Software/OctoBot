import logging

from config.cst import CONFIG_TRADER, CONFIG_TRADER_REFERENCE_MARKET, DEFAULT_REFERENCE_MARKET, \
    CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS
from trading.trader.portfolio import Portfolio, ExchangeConstantsTickersColumns
from tools.symbol_util import merge_currencies, split_symbol

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

        self.currencies_last_prices = {}
        self.origin_crypto_currencies_values = {}
        self.origin_portfolio = None
        self.last_portfolio = None

        self.portfolio_origin_value = 0
        self.portfolio_current_value = 0
        self.trades_value = 0

        self.reference_market = TradesManager.get_reference_market(self.config)

        self._init_origin_portfolio_and_currencies_value()

    @staticmethod
    def get_reference_market(config):
        # The reference market is the currency unit of the calculated quantity value
        if CONFIG_TRADER_REFERENCE_MARKET in config[CONFIG_TRADER]:
            return config[CONFIG_TRADER][CONFIG_TRADER_REFERENCE_MARKET]
        else:
            return DEFAULT_REFERENCE_MARKET

    def is_in_history(self, order):
        for trade in self.trade_history:
            if order.get_id() == trade.get_order_id():
                return True
        return False

    def get_origin_portfolio(self):
        return self.origin_portfolio

    def get_reference(self):
        return self.reference_market

    def get_trade_history(self):
        return self.trade_history

    def add_new_trade_in_history(self, trade):
        if trade not in self.trade_history:
            self.trade_history.append(trade)

    """ get currencies prices update currencies data by polling tickers from exchange
    and set currencies_prices attribute
    """

    def _update_currencies_prices(self, symbol):
        self.currencies_last_prices[symbol] = \
            self.exchange.get_price_ticker(symbol)[ExchangeConstantsTickersColumns.LAST.value]

    """ Get profitability calls get_currencies_prices to update required data
    Then calls get_portfolio_current_value to set the current value of portfolio_current_value attribute
    Returns the profitability, the profitability percentage and the difference with the last portfolio profitability
    """

    def get_profitability(self, with_market=False):
        self.profitability_diff = self.profitability_percent
        self.profitability = 0
        self.profitability_percent = 0
        market_profitability_percent = None

        try:
            current_crypto_currencies_values = self._update_portfolio_and_currencies_current_value()

            self.profitability = self.portfolio_current_value - self.portfolio_origin_value

            if self.portfolio_origin_value > 0:
                self.profitability_percent = (100 * self.portfolio_current_value / self.portfolio_origin_value) - 100
            else:
                self.profitability_percent = 0

            # calculate difference with the last current portfolio
            self.profitability_diff = self.profitability_percent - self.profitability_diff

            if with_market:
                market_profitability_percent = self.get_average_market_profitability(current_crypto_currencies_values)

        except Exception as e:
            self.logger.error(str(e))

        profitability = self.get_profitability_without_update()
        return profitability + (market_profitability_percent,)

    """ Returns the % move average of all the watched cryptocurrencies between bot's start time and now
    """

    def get_average_market_profitability(self, current_crypto_currencies_values=None):
        if current_crypto_currencies_values is None:
            current_crypto_currencies_values = self._update_portfolio_and_currencies_current_value()

        origin_values = [value / self.origin_crypto_currencies_values[currency]
                         for currency, value in current_crypto_currencies_values.items()
                         if self.origin_crypto_currencies_values[currency] > 0]

        return sum(origin_values) / len(origin_values) * 100 - 100 if len(origin_values) != 0 else 0

    def get_profitability_without_update(self):
        return self.profitability, self.profitability_percent, self.profitability_diff

    def get_portfolio_current_value(self):
        return self.portfolio_current_value

    def get_portfolio_origin_value(self):
        return self.portfolio_origin_value

    # Currently unused method
    def get_trades_value(self):
        self.trades_value = sum([self._evaluate_value(trade.get_currency(), trade.get_quantity())
                                 for trade in self.trade_history])
        return self.trades_value

    def _update_portfolio_and_currencies_current_value(self):
        current_crypto_currencies_values = self._evaluate_config_crypto_currencies_values()

        with self.portfolio as pf:
            self.last_portfolio = pf.get_portfolio()

        self.portfolio_current_value = self._evaluate_portfolio_value(self.last_portfolio,
                                                                      current_crypto_currencies_values)
        return current_crypto_currencies_values

    def _init_origin_portfolio_and_currencies_value(self):
        self.origin_crypto_currencies_values = self._evaluate_config_crypto_currencies_values()

        with self.portfolio as pf:
            self.origin_portfolio = pf.get_portfolio()

        self.portfolio_origin_value += self._evaluate_portfolio_value(self.origin_portfolio,
                                                                      self.origin_crypto_currencies_values)

    """ try_get_value_of_currency will try to obtain the current value of the currency quantity in the reference currency
    It will try to create the symbol that fit with the exchange logic
    Returns the value found of this currency quantity, if not found returns 0     
    """

    def _try_get_value_of_currency(self, currency, quantity):
        symbol = merge_currencies(currency, self.reference_market)
        symbol_inverted = merge_currencies(self.reference_market, currency)

        if self.exchange.get_exchange_manager().symbol_exists(symbol):
            self._update_currencies_prices(symbol)
            return self.currencies_last_prices[symbol] * quantity

        elif self.exchange.get_exchange_manager().symbol_exists(symbol_inverted):
            self._update_currencies_prices(symbol_inverted)
            return quantity / self.currencies_last_prices[symbol_inverted]

        else:
            self.logger.exception(f"Can't find matching symbol for {currency} and {self.reference_market}")
            return 0

    def _evaluate_config_crypto_currencies_values(self):
        values_dict = {}
        for crypto_currency_data in self.config[CONFIG_CRYPTO_CURRENCIES].values():
            pairs = crypto_currency_data[CONFIG_CRYPTO_PAIRS]
            if pairs:
                currency, _ = split_symbol(pairs[0])
                values_dict[currency] = self._evaluate_value(currency, 1)
        return values_dict

    """ evaluate_portfolio_value performs evaluate_value with a portfolio configuration
    Returns the calculated quantity value in reference (attribute) currency
    """

    def _evaluate_portfolio_value(self, portfolio, currencies_values=None):
        return sum([
            self._get_currency_value(portfolio, currency, currencies_values)
            for currency in portfolio
        ])

    def _get_currency_value(self, portfolio, currency, currencies_values=None):
        if portfolio[currency][Portfolio.TOTAL] != 0:
            if currencies_values and currency in currencies_values:
                return currencies_values[currency] * portfolio[currency][Portfolio.TOTAL]
            else:
                return self._evaluate_value(currency, portfolio[currency][Portfolio.TOTAL])
        return 0

    # Evaluate value returns the currency quantity value in the reference (attribute) currency
    def _evaluate_value(self, currency, quantity):
        # easy case --> the current currency is the reference currency
        if currency == self.reference_market:
            return quantity
        else:
            return self._try_get_value_of_currency(currency, quantity)
