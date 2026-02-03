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
import asyncio
import decimal

import octobot_commons.logging as logging
import octobot_commons.symbols as symbol_util
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.constants as commons_constants

import octobot_trading.constants as constants
import octobot_trading.errors as errors


class ValueConverter:
    """
    ValueConverter manipulates trading pairs values to extract asset values
    Uses a portfolio_manager and portfolio_value_holder to read trading pairs values
    """
    MAX_PRICE_BRIDGE_DEPTH = 6

    def __init__(self, portfolio_manager):
        self.portfolio_manager = portfolio_manager
        self._bot_main_loop = asyncio.get_event_loop()
        self.logger = logging.get_logger(f"{self.__class__.__name__}"
                                         f"[{self.portfolio_manager.exchange_manager.exchange_name}]")

        self.last_prices_by_trading_pair = {}

        self.initializing_symbol_prices = set()
        self.initializing_symbol_prices_pairs = set()

        # set of currencies for which the current exchange is not providing any suitable price data
        self.missing_currency_data_in_exchange = set()

        # internal price conversion elements
        self._price_bridge_by_symbol = {}
        self._missing_price_bridges = set()

    def update_last_price(self, symbol, price):
        if symbol not in self.last_prices_by_trading_pair:
            self.reset_missing_price_bridges()
            self.logger.debug(f"Initialized last price for {symbol}")
        self.last_prices_by_trading_pair[symbol] = price

    def evaluate_value(self, currency, quantity, raise_error=True, target_currency=None, init_price_fetchers=True):
        """
        Evaluate value returns the currency quantity value in the reference (attribute) currency
        :param currency: the currency to evaluate
        :param quantity: the currency quantity
        :param raise_error: will catch exception if False
        :param target_currency: asset to evaluate currency into, defaults to self.portfolio_manager.reference_market
        :param init_price_fetchers: will ask for missing ticker if price can't be converted if False
        :return: the currency value
        """
        target_currency = target_currency or self.portfolio_manager.reference_market
        # easy case --> the current currency is the reference currency or the quantity is 0
        if currency == target_currency or quantity == constants.ZERO:
            return quantity
        currency_value = self._try_get_value_of_currency(
            currency, quantity, target_currency, raise_error, init_price_fetchers
        )
        return self._check_currency_initialization(currency, currency_value)

    def get_usd_like_value(self, currency, quantity, raise_error=True, init_price_fetchers=True):
        if symbol_util.is_usd_like_coin(currency):
            return quantity
        if symbol := self.get_usd_like_symbol_from_symbols(currency, self.last_prices_by_trading_pair):
            base, quote = symbol_util.parse_symbol(symbol).base_and_quote()
            usd_like_currency = base if symbol_util.is_usd_like_coin(base) else quote
            return self.evaluate_value(
                currency, quantity, raise_error=raise_error,
                target_currency=usd_like_currency, init_price_fetchers=init_price_fetchers
            )
        raise errors.MissingPriceDataError(
            f"Can't convert {currency} to any of {commons_constants.USD_LIKE_COINS} using last_prices_by_trading_pair: "
            f"{list(self.last_prices_by_trading_pair)}"
        )

    @staticmethod
    def get_usd_like_symbol_from_symbols(currency: str, symbols) -> str:
        try:
            return ValueConverter.get_usd_like_symbols_from_symbols(currency, symbols)[0]
        except IndexError:
            return None

    @staticmethod
    def get_usd_like_symbols_from_symbols(currency: str, symbols) -> list:
        # look for symbols using USD_LIKE_COINS priorities
        usd_like_symbols = []
        for usd_like_coin in commons_constants.USD_LIKE_COINS:
            for symbol in symbols:
                base_and_quote = symbol_util.parse_symbol(symbol).base_and_quote()
                if currency in base_and_quote and usd_like_coin in base_and_quote:
                    usd_like_symbols.append(symbol)
        return usd_like_symbols

    @staticmethod
    def can_convert_symbol_to_usd_like(symbol: str) -> bool:
        base, quote = symbol_util.parse_symbol(symbol).base_and_quote()
        for usd_like_coins in commons_constants.USD_LIKE_COINS:
            if usd_like_coins == base or usd_like_coins == quote:
                return True
        return False

    def _check_currency_initialization(self, currency, currency_value):
        """
        Check if the currency has to be removed from self.initializing_symbol_prices and return currency_value
        :param currency: the currency to check
        :param currency_value: the currency value
        :return: currency_value after checking
        """
        if currency_value > constants.ZERO and currency in self.initializing_symbol_prices:
            self.initializing_symbol_prices.remove(currency)
        return currency_value

    def _try_get_value_of_currency(self, currency, quantity, target_currency, raise_error, init_price_fetchers):
        """
        try_get_value_of_currency will try to get the value of the given currency quantity in reference market.
        It will try to get it from a trading pair that fit with the exchange availability.
        :return: the value found of this currency quantity, if not found returns 0.
        """
        settlement_asset = self.portfolio_manager.reference_market \
            if self.portfolio_manager.exchange_manager.is_future else None
        try:
            # 1. try from existing pairs (as is and reversed)
            return self.convert_currency_value_using_last_prices(
                quantity, currency,
                target_currency,
                settlement_asset=settlement_asset
            )
        except errors.MissingPriceDataError as missing_data_exception:
            if not self.portfolio_manager.exchange_manager.is_future:
                try:
                    # 2. try from existing indirect pairs
                    value = self.try_convert_currency_value_using_multiple_pairs(
                        currency, target_currency, quantity, []
                    )
                    if value is not None:
                        return value
                except (errors.MissingPriceDataError, errors.PendingPriceDataError):
                    pass
            symbol = symbol_util.merge_currencies(
                currency, target_currency, settlement_asset=settlement_asset
            )
            reversed_symbol = symbol_util.merge_currencies(
                target_currency, currency, settlement_asset=settlement_asset
            )
            if init_price_fetchers:
                # 3. if the pair or reversed pair is traded on exchange, use it to price "currency"
                if not any(
                    self.portfolio_manager.exchange_manager.symbol_exists(s)
                    for s in (symbol, reversed_symbol)
                ) and currency not in self.missing_currency_data_in_exchange:
                    self._inform_no_matching_symbol(currency, target_currency)
                    self.missing_currency_data_in_exchange.add(currency)
                if not self.portfolio_manager.exchange_manager.is_backtesting:
                    self._try_to_ask_ticker_missing_symbol_data(currency, symbol, reversed_symbol)
            if not self.portfolio_manager.exchange_manager.is_backtesting and raise_error:
                raise missing_data_exception
        return constants.ZERO

    def _try_to_ask_ticker_missing_symbol_data(self, currency, symbol, reversed_symbol):
        """
        Try to ask the ticker producer to watch additional symbols
        to collect missing data required for profitability calculation
        :param currency: the concerned currency
        :param symbol: the symbol to add
        :param reversed_symbol: the reversed symbol to add
        """
        symbols_to_add = []
        if self.portfolio_manager.exchange_manager.symbol_exists(symbol):
            symbols_to_add = [symbol]
        elif self.portfolio_manager.exchange_manager.symbol_exists(reversed_symbol):
            symbols_to_add = [reversed_symbol]

        # Add new symbols to watched currencies.
        # Skip initializing_symbol_prices_pairs as they already have been added
        # Skip exchange_config.traded_symbol_pairs as they are already added to regular price feeds
        new_symbols_to_add = [
            s
            for s in symbols_to_add
            if s not in self.initializing_symbol_prices_pairs
            and s not in self.portfolio_manager.exchange_manager.exchange_config.traded_symbol_pairs
        ]
        if new_symbols_to_add:
            self.logger.debug(f"Fetching price for {new_symbols_to_add} to compute all the "
                              f"currencies values and properly evaluate portfolio.")
            self._ask_ticker_data_for_currency(new_symbols_to_add)
            self.initializing_symbol_prices.add(currency)
            self.initializing_symbol_prices_pairs.update(new_symbols_to_add)

    def _ask_ticker_data_for_currency(self, symbols_to_add):
        """
        Synchronously call TICKER_CHANNEL producer to add a list of new symbols to its watch list
        :param symbols_to_add: the list of symbol to add to the TICKER_CHANNEL producer watch list
        """
        if self._bot_main_loop is asyncio.get_event_loop():
            asyncio.create_task(
                self.portfolio_manager.exchange_manager.exchange_config.add_watched_symbols(symbols_to_add)
            )
        else:
            asyncio_tools.run_coroutine_in_asyncio_loop(
                self.portfolio_manager.exchange_manager.exchange_config.add_watched_symbols(symbols_to_add),
                self._bot_main_loop
            )

    def _inform_no_matching_symbol(self, currency, target_currency):
        """
        Log a missing currency pair to calculate the portfolio profitability
        :param currency: the concerned currency
        """
        # do not log warning in backtesting or tests
        if not self.portfolio_manager.exchange_manager.is_backtesting:
            self.logger.warning(f"No trading pair including {currency} and {target_currency} on"
                                f" {self.portfolio_manager.exchange_manager.exchange_name}. {currency} "
                                f"can't be valued for portfolio and profitability.")

    def convert_currency_value_using_last_prices(
        self, quantity, current_currency, target_currency, settlement_asset=None
    ):
        try:
            symbol = symbol_util.merge_currencies(
                current_currency, target_currency, settlement_asset=settlement_asset
            )
            if self._has_price_data(symbol):
                return quantity * self._get_last_price_data(symbol)
        except KeyError:
            pass
        try:
            reversed_symbol = symbol_util.merge_currencies(
                target_currency, current_currency, settlement_asset=settlement_asset
            )
            return quantity / self._get_last_price_data(reversed_symbol)
        except (KeyError, decimal.DivisionByZero, decimal.InvalidOperation):
            pass
        raise errors.MissingPriceDataError(
            f"no price data to evaluate {current_currency} price in {target_currency}"
        )

    def try_convert_currency_value_using_multiple_pairs(
            self, currency, target, quantity, base_bridge
    ) -> decimal.Decimal:
        # settlement_asset needs to be handled to add support for futures

        # try with two pairs
        # for example:
        # currency: ETH - ref market: USDT
        # ETH/USDT is not available. ETH/BTC and BTC/USDT are available though.
        # first convert ETH -> BTC and then BTC -> USDT
        #               | bridge part 1     | bridge part 2

        try:
            return self.convert_currency_value_from_saved_price_bridges(currency, target, quantity)
        except errors.MissingPriceDataError:
            if self.is_missing_price_bridge(currency, target):
                return None
            # try to find a bridge
        if len(base_bridge) > self.MAX_PRICE_BRIDGE_DEPTH:
            self._save_missing_price_bridge(currency, target)
            return None
        part_1_base = currency
        part_2_quote = target
        # look into available symbols to find pair bridges
        for bridge_part_1_symbol in self._get_priced_pairs():
            parsed_bridge_part_1_symbol = symbol_util.parse_symbol(bridge_part_1_symbol)
            if (parsed_bridge_part_1_symbol.base, parsed_bridge_part_1_symbol.quote) in base_bridge\
               or (parsed_bridge_part_1_symbol.quote, parsed_bridge_part_1_symbol.base) in base_bridge:
                # avoid looping in symbols
                continue
            # part 1: check if bridge_part_1_symbol can be used as part 1 of the bridge
            is_inverse_part_1 = False
            if part_1_base == parsed_bridge_part_1_symbol.quote:
                is_inverse_part_1 = True
            elif part_1_base != parsed_bridge_part_1_symbol.base:
                continue
            part_1_quote = parsed_bridge_part_1_symbol.quote
            if is_inverse_part_1:
                part_1_quote = parsed_bridge_part_1_symbol.base
                part_1_base = parsed_bridge_part_1_symbol.quote
            try:
                bridge_part_1_value = self.convert_currency_value_using_last_prices(
                    quantity, part_1_base, part_1_quote
                )
                # check that bridge_part_1_value is really set
                if not bridge_part_1_value:
                    continue
            except errors.MissingPriceDataError:
                # first pair might not be initialized or is not available at all
                # make sure it's not just initializing
                self._ensure_no_pending_symbol_price(part_1_base, part_1_quote)
                # try with other pairs
                continue
            # part 2: bridge part 1 is found and valued, try to get a compatible second part
            # case 1: 2 parts bridge
            try:
                bridge_part_2_value = self.convert_currency_value_using_last_prices(
                    constants.ONE,
                    part_1_quote,
                    part_2_quote,
                )
                if bridge_part_2_value:
                    self._remove_from_missing_currency_data(currency)
                    local_bridge = [(part_1_base, part_1_quote), (part_1_quote, part_2_quote)]
                    self._save_price_bridge(currency, target, local_bridge)
                    return bridge_part_1_value * bridge_part_2_value
            except errors.MissingPriceDataError:
                # conversion pairs might not be initialized or is not available at all
                self._ensure_no_pending_symbol_price(part_1_quote, part_2_quote)
                # otherwise continue with other pairs
            bridge = base_bridge + [(part_1_base, part_1_quote)]
            # case 2: X parts bridge
            nested_value = self.try_convert_currency_value_using_multiple_pairs(
                part_1_quote, target, constants.ONE, bridge
            )
            if nested_value:
                try:
                    extended_bridge = [(part_1_base, part_1_quote)] \
                        + self.get_saved_price_conversion_bridge(part_1_quote, target)
                    self._save_price_bridge(currency, target, extended_bridge)
                except KeyError:
                    # should not happen, however if it does, do not crash
                    pass
                return bridge_part_1_value * nested_value
        # no bridge found
        self._save_missing_price_bridge(currency, target)
        return None

    def _get_priced_pairs(self):
        for pair in self.last_prices_by_trading_pair:
            # first look into pairs with price
            yield pair
        for pair in self.portfolio_manager.exchange_manager.exchange_config.traded_symbol_pairs:
            # then into pairs from config
            if pair not in self.last_prices_by_trading_pair:
                yield pair
        if self.initializing_symbol_prices:
            for pair in self.initializing_symbol_prices_pairs:
                # finally into initializing pairs
                yield pair

    def _ensure_no_pending_symbol_price(self, base, quote):
        for symbol in (symbol_util.merge_currencies(base, quote), symbol_util.merge_currencies(quote, base)):
            if symbol in self.portfolio_manager.exchange_manager.exchange_config.traded_symbol_pairs \
                    or symbol in self.initializing_symbol_prices_pairs:
                raise errors.PendingPriceDataError

    def get_saved_price_conversion_bridge(self, currency, target) -> list:
        return self._price_bridge_by_symbol[symbol_util.merge_currencies(currency, target)]

    def _save_price_bridge(self, currency, target, bridge):
        self._price_bridge_by_symbol[symbol_util.merge_currencies(currency, target)] = bridge

    def convert_currency_value_from_saved_price_bridges(self, currency, target, quantity) -> decimal.Decimal:
        try:
            bridge = self._price_bridge_by_symbol[symbol_util.merge_currencies(currency, target)]
            converted_value = quantity
            for base, quote in bridge:
                converted_value = self.convert_currency_value_using_last_prices(converted_value, base, quote)
            return converted_value
        except KeyError as err:
            raise errors.MissingPriceDataError from err

    def reset_missing_price_bridges(self):
        self._missing_price_bridges = set()

    def _save_missing_price_bridge(self, base, quote):
        self._missing_price_bridges.add(symbol_util.merge_currencies(base, quote))

    def is_missing_price_bridge(self, base, quote):
        return symbol_util.merge_currencies(base, quote) in self._missing_price_bridges

    def _remove_from_missing_currency_data(self, currency):
        if currency in self.missing_currency_data_in_exchange:
            self.missing_currency_data_in_exchange.remove(currency)

    def _has_price_data(self, symbol):
        return self._get_last_price_data(symbol) is not constants.ZERO

    def _get_last_price_data(self, symbol):
        try:
            return self.last_prices_by_trading_pair[symbol]
        except KeyError:
            # a settlement asset or other symbol extra 
            # data might be different, try to ignore it
            to_find_symbol = symbol_util.parse_symbol(symbol)
            for symbol_key, last_prices in self.last_prices_by_trading_pair.items():
                if symbol_util.parse_symbol(symbol_key).is_same_base_and_quote(to_find_symbol):
                    return last_prices
        raise KeyError(symbol)

    def clear(self):
        self.portfolio_manager = None
