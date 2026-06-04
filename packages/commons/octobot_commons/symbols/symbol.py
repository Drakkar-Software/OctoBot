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
import re
import typing

import octobot_commons

_FULL_SYMBOL_GROUPS_REGEX = r"([^//]*)\/([^:]*):?([^-]*)-?([^-]*)-?([^-]*)-?([^-]*)"


# pylint: disable=R0902,R0913
class Symbol:
    #                             base   /  quote : settlement-identifier-strike price-type
    # Inspired from CCXT https://docs.ccxt.com/#/README?id=contract-naming-conventions:
    # //
    # // base asset or currency
    # // ↓
    # // ↓  quote asset or currency
    # // ↓  ↓
    # // ↓  ↓    settlement asset or currency
    # // ↓  ↓    ↓
    # // ↓  ↓    ↓       identifier (settlement date)
    # // ↓  ↓    ↓       ↓
    # // ↓  ↓    ↓       ↓   strike price
    # // ↓  ↓    ↓       ↓   ↓
    # // ↓  ↓    ↓       ↓   ↓   type, put (P) or call (C)
    # // ↓  ↓    ↓       ↓   ↓   ↓
    # 'BTC/USDT:BTC-211225-60000-P'  // BTC/USDT put option contract strike price 60000 USDT settled in BTC (inverse)
    # on 2021-12-25
    # 'ETH/USDT:USDT-211225-40000-C' // BTC/USDT call option contract strike price 40000 USDT settled in USDT (linear,
    # vanilla) on 2021-12-25
    # 'ETH/USDT:ETH-210625-5000-P'   // ETH/USDT put option contract strike price 5000 USDT settled in ETH (inverse)
    # on 2021-06-25
    # 'ETH/USDT:USDT-210625-5000-C'  // ETH/USDT call option contract strike price 5000 USDT settled in USDT (linear,
    # vanilla) on 2021-06-25
    # Local OctoBot addition (supported by the OctoBot ccxt fork)
    # Uses https://docs.ccxt.com/#/README?id=unified-networks for network names.
    # Optional network and DEX suffix (in uppercase, always at the end of the symbol):
    # 'BTC/USDT@SOL!RAYDIUM'  // BTC/USDT spot pair on solana network and raydium dex
    # 'WETH/USDT:USDT-211225-40000-C@ETH!UNISWAP'  // call option on ethereum network and uniswap dex
    # 'WETH/USDT:USDT-211225-40000-C@ETH!*'  // call option on ethereum network and any (most liquid) dex
    # Note: network and dex names cannot contain '!', which separates network from dex after '@'.

    def __init__(
        self,
        symbol_str: str,
        market_separator: str = octobot_commons.MARKET_SEPARATOR,
        settlement_separator: str = octobot_commons.SETTLEMENT_ASSET_SEPARATOR,
        option_separator: str = octobot_commons.OPTION_SEPARATOR,
        network_separator: str = octobot_commons.NETWORK_SEPARATOR,
        dex_separator: str = octobot_commons.DEX_SEPARATOR,
    ):
        self.symbol_str: str = symbol_str
        self.base: typing.Optional[str] = None
        self.quote: typing.Optional[str] = None
        self.settlement_asset: typing.Optional[str] = None
        self.identifier: typing.Optional[str] = None
        self.strike_price: typing.Optional[str] = None
        self.option_type: typing.Optional[str] = None
        self.network: typing.Optional[str] = None
        self.dex: typing.Optional[str] = None
        self.market_separator: str = market_separator
        self.settlement_separator: str = settlement_separator
        self.option_separator: str = option_separator
        self.network_separator: str = network_separator
        self.dex_separator: str = dex_separator
        self.parse_symbol(self.symbol_str)

    def parse_symbol(self, symbol_str: str):
        """
        Parse the specified symbol
        :param symbol_str: the symbol to parse
        """
        trading_symbol, self.network, self.dex = extract_network_and_dex(
            symbol_str, self.network_separator, self.dex_separator
        )
        if self.settlement_separator in trading_symbol:
            (
                self.base,
                self.quote,
                self.settlement_asset,
                self.identifier,
                self.strike_price,
                self.option_type,
            ) = _parse_symbol_full(_FULL_SYMBOL_GROUPS_REGEX, trading_symbol)
            self.option_type = _parse_option_type(self.option_type)
        else:
            # simple (probably spot) pair, use str.split as it is much faster
            self.base, self.quote = _parse_spot_symbol(
                self.market_separator, trading_symbol
            )
            self.settlement_asset = self.identifier = self.strike_price = ""
            self.option_type = None

    def base_and_quote(self) -> typing.Tuple[str, str]:
        """
        return a tuple made of this symbol's base and quote assets
        """
        return self.base, self.quote

    def merged_str_symbol(
        self,
        market_separator: str = octobot_commons.MARKET_SEPARATOR,
        settlement_separator: str = octobot_commons.SETTLEMENT_ASSET_SEPARATOR,
        option_separator: str = octobot_commons.OPTION_SEPARATOR,
        network_separator: str = octobot_commons.NETWORK_SEPARATOR,
        dex_separator: str = octobot_commons.DEX_SEPARATOR,
    ) -> str:
        """
        return the base/quote representation of this symbol. includes settlement asset if set
        """
        merged_symbol = f"{self.base}{market_separator}{self.quote}"
        if self.settlement_asset:
            merged_symbol = (
                f"{merged_symbol}{settlement_separator}{self.settlement_asset}"
            )
            if self.strike_price and self.identifier and self.option_type:
                details = [
                    "",
                    self.identifier,
                    str(self.strike_price),
                    _parse_option_type(self.option_type),
                ]
                merged_symbol = f"{merged_symbol}{option_separator.join(details)}"
        if self.network:
            merged_symbol = f"{merged_symbol}{network_separator}{self.network}"
            if self.dex:
                merged_symbol = f"{merged_symbol}{dex_separator}{self.dex}"
        return merged_symbol

    def merged_str_base_and_quote_only_symbol(
        self,
        market_separator: str = octobot_commons.MARKET_SEPARATOR,
    ):
        """
        return the base/quote representation of this symbol. includes settlement asset if set
        """
        return f"{self.base}{market_separator}{self.quote}"

    def has_network(self) -> bool:
        """
        return True when this symbol specifies a network
        """
        return bool(self.network)

    def has_dex(self) -> bool:
        """
        return True when this symbol specifies a dex
        """
        return bool(self.dex)

    def is_any_dex(self) -> bool:
        """
        return True when this symbol uses the any-dex wildcard (most liquid dex)
        """
        return self.dex == octobot_commons.ANY_DEX_WILDCARD

    def is_perpetual_future(self):
        """
        return True when this symbol is related to a perpetual future contract
        """
        return self.settlement_asset and not (
            self.identifier or self.strike_price or self.option_type
        )

    def is_spot(self):
        """
        return True when this symbol is related to a spot asset
        """
        return self.base and self.quote and not self.settlement_asset

    def is_future(self):
        """
        return True when this symbol is related to a non-perpetual future contract
        """
        return bool(
            self.settlement_asset and not (self.strike_price or self.option_type)
        )

    def does_expire(self):
        """
        return True when this symbol is related to a contract that expires
        """
        return bool(self.settlement_asset and self.identifier)

    def is_put_option(self):
        """
        return True when this symbol is related to a put option contract
        """
        return self.option_type == octobot_commons.enums.OptionTypes.PUT.value

    def is_call_option(self):
        """
        return True when this symbol is related to a call option contract
        """
        return self.option_type == octobot_commons.enums.OptionTypes.CALL.value

    def is_option(self):
        """
        return True when this symbol is related to an option contract
        """
        return bool(
            self.settlement_asset
            and self.identifier
            and self.strike_price
            and self.option_type
        )

    def is_linear(self):
        """
        return True when this symbol is related to a linear contract based on the settlement_asset
        """
        return self.quote == self.settlement_asset if self.settlement_asset else True

    def is_inverse(self):
        """
        return True when this symbol is related to an inverse contract based on the settlement_asset
        """
        return self.base == self.settlement_asset if self.settlement_asset else False

    def is_same_base_and_quote(self, other):
        """*
        :return: True if the given symbol has the same base and quote as self
        """
        return self.base == other.base and self.quote == other.quote

    def __eq__(self, other):
        return self is other or (
            isinstance(other, Symbol)
            and self.symbol_str == other.symbol_str
            and self.base == other.base
            and self.quote == other.quote
            and self.settlement_asset == other.settlement_asset
            and self.identifier == other.identifier
            and self.strike_price == other.strike_price
            and self.option_type == other.option_type
            and self.network == other.network
            and self.dex == other.dex
        )

    def __str__(self):
        return self.symbol_str

    def __repr__(self):
        return str(self)


def extract_network_and_dex(
    symbol_str: str,
    network_separator: str = octobot_commons.NETWORK_SEPARATOR,
    dex_separator: str = octobot_commons.DEX_SEPARATOR,
) -> typing.Tuple[str, typing.Optional[str], typing.Optional[str]]:
    """
    Split a symbol into its trading part and optional network/DEX suffix.
    :param symbol_str: the symbol to parse (e.g. ``BTC/USDT@SOL!RAYDIUM``)
    :param network_separator: separator before the network suffix (default ``@``)
    :param dex_separator: separator between network and dex (default ``!``)
    :return: trading symbol, network name (or None), dex name (or None)
    """
    if network_separator not in symbol_str:
        return symbol_str, None, None
    trading_symbol, network_and_dex = symbol_str.rsplit(network_separator, 1)
    if not network_and_dex:
        raise ValueError(
            f"Invalid symbol {symbol_str!r}: network must be specified after {network_separator!r}."
        )
    if dex_separator in network_and_dex:
        network, dex = network_and_dex.split(dex_separator, 1)
    else:
        network, dex = network_and_dex, None
    return trading_symbol, network, dex


def _parse_symbol_full(full_symbol_regex, symbol_str):
    return re.search(full_symbol_regex, symbol_str).groups()


def _parse_spot_symbol(separator, symbol_str):
    split_result = symbol_str.split(separator)
    if len(split_result) < 2:
        return symbol_str, None
    return split_result[0], split_result[1]


def _parse_option_type(option_type_str: typing.Optional[str]) -> typing.Optional[str]:
    return option_type_str.upper() if option_type_str else None
