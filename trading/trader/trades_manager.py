from trading.trader.portfolio import Portfolio, ExchangeConstantsTickersColumns


class TradesManager:
    def __init__(self, trader):
        self.trader = trader
        self.portfolio = trader.get_portfolio()
        self.exchange = trader.get_exchange()
        self.trades = []
        self.profitability = 0
        self.profitability_percent = 0

        # TODO : market value
        self.reported_market = "BTC"

        self.currencies_prices = None
        self.origin_portfolio = None
        self.last_portfolio = None

        self.portfolio_origin_value = 0
        self.portfolio_current_value = 0
        self.trades_value = 0

        self.get_porfolio_origin_value()

    def add_new_trade(self, trade):
        if trade not in self.trades:
            self.trades.append(trade)

    """ get currencies prices update currencies data by polling tickers from exchange
    and set currencies_prices attribute
    """
    def get_currencies_prices(self):
        self.currencies_prices = self.exchange.get_all_currencies_price_ticker()

    """ Get profitability calls get_currencies_prices to update required data
    Then calls get_portfolio_current_value to set the current value of portfolio_current_value attribute
    Returns the profitability and the profitability percentage
    """
    def get_profitability(self):
        self.profitability = 0
        self.get_currencies_prices()
        self.get_portfolio_current_value()
        self.profitability = self.portfolio_current_value - self.portfolio_origin_value
        self.profitability_percent = 100 * self.portfolio_current_value / self.portfolio_origin_value
        return self.profitability, self.profitability_percent

    def get_trades_value(self):
        self.trades_value = 0
        for trade in self.trades:
            self.trades_value += self.evaluate_value(trade.get_currency(), trade.get_quantity())
        return self.trades_value

    def get_portfolio_current_value(self):
        self.last_portfolio = self.portfolio.get_portfolio()
        self.portfolio_current_value = self.evaluate_portfolio_value(self.last_portfolio)

    def get_porfolio_origin_value(self):
        self.get_currencies_prices()
        self.origin_portfolio = self.portfolio.get_portfolio()
        self.portfolio_origin_value += self.evaluate_portfolio_value(self.origin_portfolio)

    """ try_get_value_of_currency will try to obtain the current value of the currency quantity in the reported currency
    It will try to create the symbol that fit with the exchange logic
    Returns the value found of this currency quantity, if not found returns 0     
    """
    # TODO : manage if currency/market does not exist
    def try_get_value_of_currency(self, currency, quantity):
        symbol = self.exchange.merge_currencies(currency, self.reported_market)
        symbol_inversed = self.exchange.merge_currencies(self.reported_market, currency)
        if symbol in self.currencies_prices:
            return self.currencies_prices[symbol][ExchangeConstantsTickersColumns.BID.value] * quantity
        elif symbol_inversed in self.currencies_prices:
            return self.currencies_prices[symbol_inversed][ExchangeConstantsTickersColumns.BID.value] * 1 / quantity
        else:
            return 0

    def evaluate_portfolio_value(self, portfolio):
        value = 0
        for currency in portfolio:
            value += self.evaluate_value(currency, portfolio[currency][Portfolio.TOTAL])
        return value

    # Evaluate value returns the currency quantity value in the reported (attribute) currency
    def evaluate_value(self, currency, quantity):
        # easy case --> the current currency is the reported currency
        if currency == self.reported_market:
            return quantity
        else:
            return self.try_get_value_of_currency(currency, quantity)
