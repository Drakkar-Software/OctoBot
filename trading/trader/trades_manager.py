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

from copy import deepcopy

from tools.logging.logging_util import get_logger

from config import CONFIG_TRADING, CONFIG_TRADER_REFERENCE_MARKET, DEFAULT_REFERENCE_MARKET, \
    CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS
from trading.trader.portfolio import Portfolio, ExchangeConstantsTickersColumns
from tools.symbol_util import merge_currencies, split_symbol
from trading.exchanges.exchange_simulator.exchange_simulator import ExchangeSimulator
from tools.initializable import Initializable

""" TradesManager will store all trades performed by the exchange trader
Another feature of TradesManager is the profitability calculation
by subtracting portfolio_current_value and portfolio_origin_value """


class TradesManager(Initializable):

    def __init__(self, config, trader):
        super().__init__()
        self.config = config
        self.trader = trader
        self.portfolio = trader.get_portfolio()
        self.exchange = trader.get_exchange()
        self.logger = get_logger(self.__class__.__name__)

        self.trade_history = []
        self.profitability = 0
        self.profitability_percent = 0
        self.profitability_diff = 0

        self.currencies_last_prices = {}
        self.origin_crypto_currencies_values = {}
        self.current_crypto_currencies_values = {}
        self.origin_portfolio = None

        # buffer of currencies excluding market only used currencies ex: conf = btc/usd, eth/btc, ltc/btc, here usd
        # is market only => not used to compute market average profitability
        self.traded_currencies_without_market_specific = set()

        # buffer of currencies containing currencies that have already been logged as without matching symbol
        # (used not to spam logs)
        self.already_informed_no_matching_symbol_currency = set()

        self.portfolio_origin_value = 0
        self.portfolio_current_value = 0
        self.trades_value = 0

        self.reference_market = TradesManager.get_reference_market(self.config)

    async def initialize_impl(self):
        await self._init_origin_portfolio_and_currencies_value()

    @staticmethod
    def get_reference_market(config):
        # The reference market is the currency unit of the calculated quantity value
        if CONFIG_TRADER_REFERENCE_MARKET in config[CONFIG_TRADING]:
            return config[CONFIG_TRADING][CONFIG_TRADER_REFERENCE_MARKET]
        else:
            return DEFAULT_REFERENCE_MARKET

    def is_in_history(self, order):
        return any([order.get_id() == trade.order_id for trade in self.trade_history])

    def get_origin_portfolio(self):
        return self.origin_portfolio

    def get_reference(self):
        return self.reference_market

    def get_trade_history(self):
        return self.trade_history

    def select_trade_history(self, symbol=None):
        return [trade for trade in self.trade_history if trade.symbol == symbol] \
            if symbol is not None else self.trade_history

    def add_new_trade_in_history(self, trade):
        if trade not in self.trade_history:
            self.trade_history.append(trade)

    """ get currencies prices update currencies data by polling tickers from exchange
    and set currencies_prices attribute
    """

    async def _update_currencies_prices(self, symbol):
        ticker = await self.exchange.get_price_ticker(symbol)
        self.currencies_last_prices[symbol] = ticker[ExchangeConstantsTickersColumns.LAST.value]

    """ Get profitability calls get_currencies_prices to update required data
    Then calls get_portfolio_current_value to set the current value of portfolio_current_value attribute
    Returns the profitability, the profitability percentage and the difference with the last portfolio profitability
    """

    async def get_profitability(self, with_market=False):
        self.profitability_diff = self.profitability_percent
        self.profitability = 0
        self.profitability_percent = 0
        market_profitability_percent = None
        initial_portfolio_current_profitability = 0

        try:
            await self._update_portfolio_and_currencies_current_value()
            initial_portfolio_current_value = await self._get_origin_portfolio_current_value()

            self.profitability = self.portfolio_current_value - self.portfolio_origin_value

            if self.portfolio_origin_value > 0:
                self.profitability_percent = (100 * self.portfolio_current_value / self.portfolio_origin_value) - 100
                initial_portfolio_current_profitability = \
                    (100 * initial_portfolio_current_value / self.portfolio_origin_value) - 100
            else:
                self.profitability_percent = 0

            # calculate difference with the last current portfolio
            self.profitability_diff = self.profitability_percent - self.profitability_diff

            if with_market:
                market_profitability_percent = await self.get_average_market_profitability()

        except Exception as e:
            self.logger.error(str(e))
            self.logger.exception(e)

        profitability = self.get_profitability_without_update()
        return profitability + (market_profitability_percent, initial_portfolio_current_profitability)

    """ Returns the % move average of all the watched cryptocurrencies between bot's start time and now
    """

    async def get_average_market_profitability(self):
        await self.get_current_crypto_currencies_values()

        origin_values = [value / self.origin_crypto_currencies_values[currency]
                         for currency, value
                         in self.only_symbol_currency_filter(self.current_crypto_currencies_values).items()
                         if self.origin_crypto_currencies_values[currency] > 0]

        return sum(origin_values) / len(origin_values) * 100 - 100 if origin_values else 0

    async def get_current_crypto_currencies_values(self):
        if not self.current_crypto_currencies_values:
            await self._update_portfolio_and_currencies_current_value()
        return self.current_crypto_currencies_values

    async def get_current_holdings_values(self):
        holdings = await self.get_current_crypto_currencies_values()

        async with self.portfolio.get_lock():
            current_portfolio = deepcopy(self.portfolio.get_portfolio())

        return {currency: await self._get_currency_value(current_portfolio, currency, holdings)
                for currency in holdings.keys()}

    def get_profitability_without_update(self):
        return self.profitability, self.profitability_percent, self.profitability_diff

    def get_portfolio_current_value(self):
        return self.portfolio_current_value

    def get_portfolio_origin_value(self):
        return self.portfolio_origin_value

    def only_symbol_currency_filter(self, currency_dict):
        if not self.traded_currencies_without_market_specific:
            self.init_traded_currencies_without_market_specific()
        return {currency: v for currency, v in currency_dict.items()
                if currency in self.traded_currencies_without_market_specific}

    def init_traded_currencies_without_market_specific(self):
        for crypto_currency in self.config[CONFIG_CRYPTO_CURRENCIES].values():
            for pair in crypto_currency[CONFIG_CRYPTO_PAIRS]:
                symbol, _ = split_symbol(pair)
                if symbol not in self.traded_currencies_without_market_specific:
                    self.traded_currencies_without_market_specific.add(symbol)

    async def _update_portfolio_and_currencies_current_value(self):
        async with self.portfolio.get_lock():
            current_portfolio = deepcopy(self.portfolio.get_portfolio())

        self.portfolio_current_value = await self._update_portfolio_current_value(current_portfolio)

    async def _init_origin_portfolio_and_currencies_value(self):
        self.origin_crypto_currencies_values = await self._evaluate_config_crypto_currencies_values()
        async with self.portfolio.get_lock():
            self.origin_portfolio = deepcopy(self.portfolio.get_portfolio())

        self.portfolio_origin_value = \
            await self._update_portfolio_current_value(self.origin_portfolio,
                                                       currencies_values=self.origin_crypto_currencies_values)

    async def _get_origin_portfolio_current_value(self, refresh_values=False):
        if refresh_values:
            self.current_crypto_currencies_values = await self._evaluate_config_crypto_currencies_values()
        return await self._update_portfolio_current_value(self.origin_portfolio,
                                                          currencies_values=self.current_crypto_currencies_values)

    async def _update_portfolio_current_value(self, portfolio, currencies_values=None):
        values = currencies_values
        if values is None:
            self.current_crypto_currencies_values = await self._evaluate_config_crypto_currencies_values()
            values = self.current_crypto_currencies_values
        return await self._evaluate_portfolio_value(portfolio, values)

    """ try_get_value_of_currency will try to obtain the current value of the currency quantity
    in the reference currency.
    It will try to create the symbol that fit with the exchange logic.
    Returns the value found of this currency quantity, if not found returns 0.   
    """

    async def _try_get_value_of_currency(self, currency, quantity):
        symbol = merge_currencies(currency, self.reference_market)
        symbol_inverted = merge_currencies(self.reference_market, currency)

        if self.exchange.get_exchange_manager().symbol_exists(symbol):
            await self._update_currencies_prices(symbol)
            return self.currencies_last_prices[symbol] * quantity

        elif self.exchange.get_exchange_manager().symbol_exists(symbol_inverted):
            await self._update_currencies_prices(symbol_inverted)
            return quantity / self.currencies_last_prices[symbol_inverted]

        else:
            self._inform_no_matching_symbol(currency)
            return 0

    def _inform_no_matching_symbol(self, currency, force=False):
        if force or currency not in self.already_informed_no_matching_symbol_currency:
            self.already_informed_no_matching_symbol_currency.add(currency)
            if not isinstance(self.exchange.get_exchange(), ExchangeSimulator):
                # do not log warning in backtesting or tests
                self.logger.warning(f"Can't find matching symbol for {currency} and {self.reference_market}")
            else:
                self.logger.info(f"Can't find matching symbol for {currency} and {self.reference_market}")

    async def _evaluate_config_crypto_currencies_values(self):
        values_dict = {}
        evaluated_currencies = set()
        for crypto_currency_data in self.config[CONFIG_CRYPTO_CURRENCIES].values():
            pairs = crypto_currency_data[CONFIG_CRYPTO_PAIRS]
            if pairs:
                currency, market = split_symbol(pairs[0])
                if currency not in evaluated_currencies:
                    values_dict[currency] = await self._evaluate_value(currency, 1)
                    evaluated_currencies.add(currency)
                if market not in evaluated_currencies:
                    values_dict[market] = await self._evaluate_value(market, 1)
                    evaluated_currencies.add(market)
        return values_dict

    """ evaluate_portfolio_value performs evaluate_value with a portfolio configuration
    Returns the calculated quantity value in reference (attribute) currency
    """

    async def _evaluate_portfolio_value(self, portfolio, currencies_values=None):
        return sum([
            await self._get_currency_value(portfolio, currency, currencies_values)
            for currency in portfolio
        ])

    async def _get_currency_value(self, portfolio, currency, currencies_values=None):
        if currency in portfolio and portfolio[currency][Portfolio.TOTAL] != 0:
            if currencies_values and currency in currencies_values:
                return currencies_values[currency] * portfolio[currency][Portfolio.TOTAL]
            else:
                return await self._evaluate_value(currency, portfolio[currency][Portfolio.TOTAL])
        return 0

    # Evaluate value returns the currency quantity value in the reference (attribute) currency
    async def _evaluate_value(self, currency, quantity):
        # easy case --> the current currency is the reference currency
        if currency == self.reference_market:
            return quantity
        else:
            return await self._try_get_value_of_currency(currency, quantity)
