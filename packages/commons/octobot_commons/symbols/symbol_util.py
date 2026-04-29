# pylint: disable=R0913
#  Drakkar-Software OctoBot-Commons
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
import functools
import typing
import collections

import octobot_commons
import octobot_commons.constants as constants
import octobot_commons.symbols.symbol


_MAX_PARSED_SYMBOLS_CACHE_SIZE = 2048


@functools.lru_cache(maxsize=_MAX_PARSED_SYMBOLS_CACHE_SIZE)
def parse_symbol(symbol: str):
    """
    Parse the specified symbol into a Symbol object
    :param symbol: the symbol to parse
    :return: Symbol object
    """
    return octobot_commons.symbols.symbol.Symbol(symbol)


def merge_symbol(symbol: str) -> str:
    """
    Return merged currency and market without /
    :param symbol: the specified symbol
    :return: merged currency and market without /
    """
    return symbol.replace(octobot_commons.MARKET_SEPARATOR, "").replace(
        octobot_commons.SETTLEMENT_ASSET_SEPARATOR, "_"
    )


def is_symbol(value: str, separator: str = octobot_commons.MARKET_SEPARATOR) -> bool:
    """
    Check if the given string is a symbol or a coin based on the separator
    :param value: the string to check
    :param separator: the separator to use for checking (e.g., "/" for "BTC/USDT")
    :return: True if the string is a symbol (contains the separator), False if it's a coin (single currency)
    """
    return separator in value


def merge_currencies(
    currency: str,
    market: str,
    settlement_asset: typing.Optional[str] = None,
    identifier: typing.Optional[str] = None,
    strike_price: typing.Optional[str] = None,
    option_type: typing.Optional[str] = None,
    market_separator: str = octobot_commons.MARKET_SEPARATOR,
    settlement_separator: str = octobot_commons.SETTLEMENT_ASSET_SEPARATOR,
    option_separator: str = octobot_commons.OPTION_SEPARATOR,
) -> str:
    """
    Merge currency and market
    :param currency: the base currency
    :param market: the quote currency
    :param settlement_asset: the settlement asset currency (unused for spot trading)
    :param strike_price: the strike price or time (used for options)
    :param market_separator: the separator between currency and market
    :param settlement_separator: the separator between the pair and reference market
    :param option_separator: the separator between the option details
    :return: currency and market merged
    """
    symbol = octobot_commons.symbols.symbol.Symbol(
        f"{currency}{market_separator}{market}", market_separator=market_separator
    )
    if settlement_asset is not None:
        symbol.settlement_asset = settlement_asset
    if strike_price:
        symbol.strike_price = strike_price
    if identifier:
        symbol.identifier = identifier
    if option_type:
        symbol.option_type = option_type
    return symbol.merged_str_symbol(
        market_separator=market_separator,
        settlement_separator=settlement_separator,
        option_separator=option_separator,
    )


def convert_symbol(
    symbol: str,
    symbol_separator: str,
    new_symbol_separator: str = octobot_commons.MARKET_SEPARATOR,
    should_uppercase: bool = False,
    should_lowercase: bool = False,
    base_and_quote_only: bool = False,
) -> str:
    """
    Convert symbol according to parameter
    :param symbol: the symbol to convert
    :param symbol_separator: the symbol separator
    :param new_symbol_separator: the new symbol separator
    :param should_uppercase: if it should be concerted to uppercase
    :param should_lowercase: if it should be concerted to lowercase
    :param base_and_quote_only: if it should only contain base and quote from the given symbol
    :return:
    """
    if base_and_quote_only:
        symbol = symbol.split(octobot_commons.SETTLEMENT_ASSET_SEPARATOR)[0]
    if should_uppercase:
        return symbol.replace(symbol_separator, new_symbol_separator).upper()
    if should_lowercase:
        return symbol.replace(symbol_separator, new_symbol_separator).lower()
    return symbol.replace(symbol_separator, new_symbol_separator)


def is_usd_like_coin(coin: str) -> bool:
    """
    :return: True if the given coin is a USD-like coin
    """
    return coin in constants.USD_LIKE_COINS


def get_most_common_usd_like_symbol(pairs: list[str]) -> str:
    """
    :return: The most common USD like symbol from the given pairs
    """
    if not pairs:
        raise ValueError("Pairs cannot be empty")
    symbols = []
    for pair in pairs:
        parsed = octobot_commons.symbols.symbol.Symbol(pair)
        symbols.append(parsed.quote)
        symbols.append(parsed.base)
    counter = collections.Counter(symbols)
    for symbol, _ in counter.most_common():
        if is_usd_like_coin(symbol):
            return symbol
    raise ValueError("Pairs cannot be empty")
