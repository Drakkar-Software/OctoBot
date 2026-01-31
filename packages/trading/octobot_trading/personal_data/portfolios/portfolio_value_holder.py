#  Drakkar-Software OctoBot-Trading
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
import typing
import decimal

import octobot_commons.logging as logging
import octobot_commons.symbols as symbol_util

import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.enums as enums
import octobot_trading.personal_data.portfolios.value_converter as value_converter
import octobot_trading.personal_data.portfolios


class PortfolioValueHolder:
    """
    PortfolioValueHolder calculates the current and the origin portfolio value in reference market for each updates
    """

    def __init__(self, portfolio_manager):
        self.portfolio_manager: octobot_trading.personal_data.portfolios.PortfolioManager = portfolio_manager
        self.logger: logging.BotLogger = logging.get_logger(f"{self.__class__.__name__}"
                                         f"[{self.portfolio_manager.exchange_manager.exchange_name}]")
        self.value_converter: value_converter.ValueConverter = value_converter.ValueConverter(self.portfolio_manager)

        self.portfolio_origin_value: decimal.Decimal = constants.ZERO
        self.portfolio_current_value: decimal.Decimal = constants.ZERO

        # values in decimal.Decimal
        self.origin_portfolio: typing.Optional[octobot_trading.personal_data.portfolios.Portfolio] = None

        # values in decimal.Decimal
        self.origin_crypto_currencies_values: dict[str, decimal.Decimal] = {}
        self.current_crypto_currencies_values: dict[str, decimal.Decimal] = {}

    def reset_portfolio_values(self):
        self.portfolio_origin_value = constants.ZERO
        self.portfolio_current_value = constants.ZERO

        self.origin_portfolio = None

        self.origin_crypto_currencies_values = {}
        self.current_crypto_currencies_values = {}

    def update_origin_crypto_currencies_values(self, symbol, mark_price):
        """
        Update origin cryptocurrencies value
        :param symbol: the symbol to update
        :param mark_price: the symbol mark price value in decimal.Decimal
        :return: True if the origin portfolio should be recomputed
        """
        currency, market = symbol_util.parse_symbol(symbol).base_and_quote()
        # update origin values if this price has relevant data regarding
        # the origin portfolio (using both quote and base)
        origin_crypto_currencies_with_values = set(self.origin_crypto_currencies_values.keys())
        origin_currencies_should_be_updated = (
            (
                currency not in origin_crypto_currencies_with_values
                and currency != self.portfolio_manager.reference_market
            )
            or
            (
                market not in origin_crypto_currencies_with_values
                and market != self.portfolio_manager.reference_market
            )
        )
        self.value_converter.update_last_price(symbol, mark_price)
        if origin_currencies_should_be_updated:
            # Will fail if symbol doesn't have a price in
            # self.origin_crypto_currencies_values and therefore
            # requires the origin portfolio value to be recomputed 
            # using this price info in case this price is relevant
            if market == self.portfolio_manager.reference_market:
                self.origin_crypto_currencies_values[currency] = mark_price
            elif currency == self.portfolio_manager.reference_market:
                self.origin_crypto_currencies_values[market] = constants.ONE / mark_price
            else:
                try:
                    converted_value = self.value_converter.try_convert_currency_value_using_multiple_pairs(
                        currency, self.portfolio_manager.reference_market, constants.ONE, []
                    )
                    if converted_value is not None:
                        self.origin_crypto_currencies_values[currency] = converted_value
                except (errors.MissingPriceDataError, errors.PendingPriceDataError):
                    pass
        return origin_currencies_should_be_updated

    def get_current_crypto_currencies_values(self):
        """
        Return the current crypto-currencies values
        :return: the current crypto-currencies values
        """
        if not self.current_crypto_currencies_values:
            self.sync_portfolio_current_value_using_available_currencies_values()
        return self.current_crypto_currencies_values

    def get_current_holdings_values(self):
        """
        Get holdings ratio for each currency
        :return: the holdings ratio dictionary
        """
        holdings = self.get_current_crypto_currencies_values()
        return {
            currency: self._get_currency_value(self.portfolio_manager.portfolio.portfolio, currency, holdings)
            for currency in holdings.keys()
        }

    def get_assets_holdings_value(self, assets, target_unit, init_price_fetchers=False):
        total_value = constants.ZERO
        for asset, asset_holdings in self.portfolio_manager.portfolio.portfolio.items():
            if asset not in assets:
                continue
            try:
                total_value += self.value_converter.evaluate_value(
                    asset, asset_holdings.total, raise_error=True,
                    target_currency=target_unit, init_price_fetchers=init_price_fetchers
                )
            except errors.MissingPriceDataError:
                self.logger.info(f"Missing {asset} price conversion, ignoring {float(asset_holdings.total)} holdings.")
        return total_value

    def _get_orders_delta(self, currency: str) -> decimal.Decimal:
        """
        Gets the orders delta for a currency.
        """
        assets_in_open_orders = constants.ZERO
        for order in self.portfolio_manager.exchange_manager.exchange_personal_data.orders_manager.get_open_orders():
            symbol = symbol_util.parse_symbol(order.symbol)
            if order.side is enums.TradeOrderSide.BUY and symbol.base == currency:
                assets_in_open_orders += order.origin_quantity
            elif order.side is enums.TradeOrderSide.SELL and symbol.quote == currency:
                assets_in_open_orders += order.total_cost
        return assets_in_open_orders

    def _get_open_orders_value_for_symbol(self, symbol: str) -> decimal.Decimal:
        """
        Get the net pending order value for a specific symbol.
        For options/futures, orders are matched by their full symbol.
        Buy orders increase the value (pending acquisition), sell orders decrease it (pending disposal).
        :param symbol: the full symbol (e.g., 'BTC/USDC:USDC')
        :return: the net pending order value in the settlement currency
        """
        total_order_value = constants.ZERO
        orders_manager = self.portfolio_manager.exchange_manager.exchange_personal_data.orders_manager
        for order in orders_manager.get_open_orders(symbol=symbol):
            pending_quantity = order.origin_quantity - order.filled_quantity
            order_value = pending_quantity * order.origin_price
            if order.side is enums.TradeOrderSide.BUY:
                total_order_value += order_value
            elif order.side is enums.TradeOrderSide.SELL:
                total_order_value -= order_value
        return total_order_value

    def handle_profitability_recalculation(self, force_recompute_origin_portfolio):
        """
        Initialize values required by portfolio profitability to perform its profitability calculation
        :param force_recompute_origin_portfolio: when True, force origin portfolio computation
        """
        self.sync_portfolio_current_value_using_available_currencies_values()
        self._init_portfolio_values_if_necessary(force_recompute_origin_portfolio)

    def get_origin_portfolio_current_value(self, refresh_values=False):
        """
        Calculates and return the origin portfolio actual value
        :param refresh_values: when True, force origin portfolio reevaluation
        :return: the origin portfolio current value
        """
        if refresh_values:
            self.current_crypto_currencies_values.update(
                self._evaluate_config_crypto_currencies_and_portfolio_values(self.origin_portfolio.portfolio)
            )
        return self._update_portfolio_current_value(
            self.origin_portfolio.portfolio, currencies_values=self.current_crypto_currencies_values
        )

    def _init_portfolio_values_if_necessary(self, force_recompute_origin_portfolio):
        """
        Init origin portfolio values if necessary
        :param force_recompute_origin_portfolio: when True, force origin portfolio computation
        """
        if self.portfolio_origin_value == constants.ZERO:
            # try to update portfolio origin value if it's not known yet
            self._init_origin_portfolio_and_currencies_value()
        if force_recompute_origin_portfolio:
            self._recompute_origin_portfolio_initial_value()

    def _init_origin_portfolio_and_currencies_value(self):
        """
        Initialize origin portfolio and the origin portfolio currencies values
        """
        self.origin_portfolio = self.origin_portfolio or copy.copy(self.portfolio_manager.portfolio)
        self.origin_crypto_currencies_values.update(
            self._evaluate_config_crypto_currencies_and_portfolio_values(
                self.origin_portfolio.portfolio,
                ignore_missing_currency_data=True
            )
        )
        self._recompute_origin_portfolio_initial_value()

    def _update_portfolio_current_value(
        self, portfolio, currencies_values=None, fill_currencies_values=False, init_price_fetchers=True
    ):
        """
        Update the portfolio with current prices
        :param portfolio: the portfolio to update
        :param currencies_values: the currencies values
        :param fill_currencies_values: the currencies values to calculate
        :param init_price_fetchers: When True, can init price using fetchers
        :return: the updated portfolio
        """
        values = currencies_values
        if values is None or fill_currencies_values:
            value_update = self._evaluate_config_crypto_currencies_and_portfolio_values(
                portfolio, init_price_fetchers=init_price_fetchers
            )
            self.current_crypto_currencies_values.update(value_update)
            if len(self.current_crypto_currencies_values) > len(self.origin_crypto_currencies_values):
                # add any missing value to origin_crypto_currencies_values (can happen with indirect valuations)
                self._fill_currencies_values(self.origin_crypto_currencies_values)
            if fill_currencies_values:
                self._fill_currencies_values(currencies_values)
            values = self.current_crypto_currencies_values
        return self._evaluate_portfolio_value(portfolio, values, init_price_fetchers=init_price_fetchers)

    def _fill_currencies_values(self, currencies_values):
        """
        Fill a currency values dict with new data
        :param currencies_values: currencies values dict to be filled
        """
        currencies_values.update({
            currency: value
            for currency, value in self.current_crypto_currencies_values.items()
            if currency not in currencies_values
        })

    def sync_portfolio_current_value_using_available_currencies_values(self, init_price_fetchers=True):
        """
        :param init_price_fetchers: When True, can init price using fetchers
        Update the portfolio current value with the current portfolio instance
        """
        self.portfolio_current_value = self._update_portfolio_current_value(
            self.portfolio_manager.portfolio.portfolio, init_price_fetchers=init_price_fetchers
        )

    def _recompute_origin_portfolio_initial_value(self):
        """
        Compute origin portfolio initial value and update portfolio_origin_value
        """
        if self.portfolio_manager.historical_portfolio_value_manager is not None \
           and self.portfolio_manager.historical_portfolio_value_manager.has_historical_starting_portfolio_value(
            self.portfolio_manager.reference_market
        ):
            # get origin value from history when possible
            value = self.portfolio_manager.historical_portfolio_value_manager.\
                get_historical_starting_starting_portfolio_value(self.portfolio_manager.reference_market)
            if value is not None:
                self.portfolio_origin_value = value
                return
        self.portfolio_origin_value = self._update_portfolio_current_value(
            self.origin_portfolio.portfolio,
            currencies_values=self.origin_crypto_currencies_values,
            fill_currencies_values=True
        )

    def _evaluate_config_crypto_currencies_and_portfolio_values(
        self, portfolio, ignore_missing_currency_data=False, init_price_fetchers=True
    ):
        """
        Evaluate both config and portfolio currencies values
        :param portfolio: the current portfolio
        :param ignore_missing_currency_data: when True, ignore missing currencies values in calculation
        :param init_price_fetchers: When True, can init price using fetchers
        :return: the result of config and portfolio currencies values calculation
        """
        evaluated_pair_values = {}
        evaluated_currencies = set()
        missing_tickers = set()

        self._evaluate_config_currencies_values(
            evaluated_pair_values, evaluated_currencies, missing_tickers,
            init_price_fetchers=init_price_fetchers
        )
        self._evaluate_portfolio_currencies_values(
            portfolio, evaluated_pair_values, evaluated_currencies,
            missing_tickers, ignore_missing_currency_data, init_price_fetchers=init_price_fetchers
        )
        return evaluated_pair_values

    def _evaluate_config_currencies_values(self, evaluated_pair_values, evaluated_currencies, missing_tickers, init_price_fetchers=True):
        """
        Evaluate config currencies values
        :param evaluated_pair_values: the list of evaluated pairs
        :param evaluated_currencies: the list of evaluated currencies
        :param missing_tickers: the list of missing currencies
        :param init_price_fetchers: When True, can init price using fetchers
        """
        if self.portfolio_manager.exchange_manager.exchange_config.traded_symbols:
            currency, market = \
                self.portfolio_manager.exchange_manager.exchange_config.traded_symbols[0].base_and_quote()
            currency_to_evaluate = currency
            try:
                if currency not in evaluated_currencies:
                    evaluated_pair_values[currency] = self.value_converter.evaluate_value(
                        currency, constants.ONE, init_price_fetchers=init_price_fetchers
                    )
                    evaluated_currencies.add(currency)
                if market not in evaluated_currencies:
                    currency_to_evaluate = market
                    evaluated_pair_values[market] = self.value_converter.evaluate_value(
                        market, constants.ONE, init_price_fetchers=init_price_fetchers
                    )
                    evaluated_currencies.add(market)
            except errors.MissingPriceDataError:
                missing_tickers.add(currency_to_evaluate)

    def _evaluate_portfolio_currencies_values(
        self,
        portfolio,
        evaluated_pair_values,
        evaluated_currencies,
        missing_tickers,
        ignore_missing_currency_data,
        init_price_fetchers=True
    ):
        """
        Evaluate current portfolio currencies values
        :param portfolio: the current portfolio
        :param evaluated_pair_values: the list of evaluated pairs
        :param evaluated_currencies: the list of evaluated currencies
        :param missing_tickers: the list of missing currencies
        :param ignore_missing_currency_data: when True, ignore missing currencies values in calculation
        :param init_price_fetchers: When True, can init price using fetchers
        """
        for currency in portfolio:
            try:
                if currency not in evaluated_currencies and self._should_currency_be_considered(
                        currency, portfolio, ignore_missing_currency_data
                ):
                    evaluated_pair_values[currency] = self.value_converter.evaluate_value(
                        currency, constants.ONE, init_price_fetchers=init_price_fetchers
                    )
                    evaluated_currencies.add(currency)
            except errors.MissingPriceDataError:
                missing_tickers.add(currency)

    def _evaluate_portfolio_value(self, portfolio, currencies_values=None, init_price_fetchers=True):
        """
        Perform evaluate_value with a portfolio configuration
        :param portfolio: the portfolio to explore
        :param currencies_values: currencies to evaluate
        :param init_price_fetchers: When True, can init price using fetchers
        :return: the calculated quantity value in reference (attribute) currency
        """
        return sum([
            self._get_currency_value(portfolio, currency, currencies_values, init_price_fetchers=init_price_fetchers)
            for currency in portfolio
            if currency not in self.value_converter.missing_currency_data_in_exchange
        ])

    def _get_currency_value(self, portfolio, currency, currencies_values=None, raise_error=False, init_price_fetchers=True):
        """
        Return the currency value
        :param portfolio: the specified portfolio
        :param currency: the currency to evaluate
        :param currencies_values: currencies values dict
        :param raise_error: When True, forward exceptions
        :param init_price_fetchers: When True, can init price using fetchers
        :return: the currency value
        """
        if currency in portfolio and portfolio[currency].total != constants.ZERO:
            if currencies_values and currency in currencies_values:
                return currencies_values[currency] * portfolio[currency].total
            return self.value_converter.evaluate_value(
                currency, portfolio[currency].total, 
                raise_error=raise_error, init_price_fetchers=init_price_fetchers
            )
        return constants.ZERO

    def _should_currency_be_considered(self, currency, portfolio, ignore_missing_currency_data):
        """
        Return True if enough data is available to evaluate currency value
        :param currency: the currency to evaluate
        :param portfolio: the specified portfolio
        :param ignore_missing_currency_data: When True, ignore check of currency presence
        in missing_currency_data_in_exchange
        :return: True if enough data is available to evaluate currency value
        """
        return (
            currency not in self.value_converter.missing_currency_data_in_exchange or ignore_missing_currency_data
        ) and (
            portfolio[currency].total > constants.ZERO
            or currency in self.portfolio_manager.portfolio_profitability.valuated_currencies
        )

    def _get_total_holdings_value(self, coins_whitelist=None, traded_symbols_only=False) -> decimal.Decimal:
        """
        Get the total holdings value
        :param coins_whitelist: the coins whitelist
        :param traded_symbols_only: when True, only consider traded symbols
        :return: the total holdings value
        """
        if coins_whitelist and not traded_symbols_only:
            total_holdings_value = self.get_assets_holdings_value(
                coins_whitelist, self.portfolio_manager.reference_market
            )
        elif traded_symbols_only:
            total_holdings_value = self.get_traded_assets_holdings_value(
                self.portfolio_manager.reference_market, coins_whitelist
            )
        else:
            # consider all assets for total_holdings_value
            total_holdings_value = self.portfolio_current_value
        if not total_holdings_value:
            return constants.ZERO
        return total_holdings_value

    def _get_total_holdings_in_open_orders(self, currency: str) -> decimal.Decimal:
        """
        Get the total holdings in open orders
        :param currency: the currency to evaluate
        :return: the total holdings in open orders
        """
        assets_in_open_orders = self._get_orders_delta(currency)
        return assets_in_open_orders

    def _get_holdings_ratio_from_portfolio(self, currency, traded_symbols_only=False, include_assets_in_open_orders=False, coins_whitelist=None) -> decimal.Decimal:
        """
        Get the holdings ratio from the portfolio
        :param currency: the currency to evaluate
        :param traded_symbols_only: when True, only consider traded symbols
        :param include_assets_in_open_orders: when True, include assets in open orders
        :param coins_whitelist: the coins whitelist
        :return: the holdings ratio
        """
        total_holdings_value = self._get_total_holdings_value(coins_whitelist=coins_whitelist, traded_symbols_only=traded_symbols_only)

        currency_holdings = self.portfolio_manager.portfolio.get_currency_portfolio(currency).total
        if include_assets_in_open_orders:
            currency_holdings += self._get_total_holdings_in_open_orders(currency)

        current_holdings_value = self.value_converter.evaluate_value(currency, currency_holdings, init_price_fetchers=False)
        if total_holdings_value > constants.ZERO:
            currency_holdings_ratio = current_holdings_value / total_holdings_value
            return currency_holdings_ratio
        return constants.ZERO

    def get_traded_assets_holdings_value(self, unit: str, coins_whitelist: typing.Optional[typing.Iterable]) -> decimal.Decimal:
        """
        Get the traded assets holdings value
        :param unit: the unit to evaluate
        :param coins_whitelist: the coins whitelist
        :return: the traded assets holdings value
        """
        assets = set()
        additional_traded_symbols = [symbol_util.parse_symbol(symbol) for symbol in self.portfolio_manager.exchange_manager.exchange_config.additional_traded_pairs]
        for symbol in self.portfolio_manager.exchange_manager.exchange_config.traded_symbols + additional_traded_symbols:
            if coins_whitelist is None or symbol.base in coins_whitelist:
                assets.add(symbol.base)
            if coins_whitelist is None or symbol.quote in coins_whitelist:
                assets.add(symbol.quote)
        return self.get_assets_holdings_value(
            assets, unit
        )

    def get_holdings_ratio(
        self, currency, traded_symbols_only=False, include_assets_in_open_orders=False, coins_whitelist=None
    ) -> typing.Optional[decimal.Decimal]:
        raise NotImplementedError("get_holdings_ratio is not implemented")

    def clear(self):
        self.value_converter.clear()
        self.value_converter = None # type: ignore
        self.portfolio_manager = None # type: ignore
