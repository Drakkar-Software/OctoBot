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
#  License along with this library
import collections
import octobot_commons.constants as commons_constants
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_commons.symbols as symbol_util


def is_trading_paused(config) -> bool:
    try:
        return config[commons_constants.CONFIG_TRADING][commons_constants.CONFIG_TRADER_PAUSED]
    except KeyError:
        return False


def is_trader_enabled(config) -> bool:
    return _is_trader_enabled(config, commons_constants.CONFIG_TRADER)


def is_trader_simulator_enabled(config) -> bool:
    return _is_trader_enabled(config, commons_constants.CONFIG_SIMULATOR)


def _is_trader_enabled(config, trader_key) -> bool:
    try:
        return config[trader_key][commons_constants.CONFIG_ENABLED_OPTION]
    except KeyError:
        if trader_key not in config:
            config[trader_key] = {}
        config[trader_key][commons_constants.CONFIG_ENABLED_OPTION] = False
        return False


def is_trade_history_loading_enabled(config, default=True) -> bool:
    try:
        return config[commons_constants.CONFIG_TRADER].get(commons_constants.CONFIG_LOAD_TRADE_HISTORY, default)
    except KeyError:
        return default


def is_currency_enabled(config, currency, default_value) -> bool:
    try:
        return config[commons_constants.CONFIG_CRYPTO_CURRENCIES][currency][commons_constants.CONFIG_ENABLED_OPTION]
    except KeyError:
        return default_value


def is_symbol_disabled(config, symbol) -> bool:
    for currency_details in config[commons_constants.CONFIG_CRYPTO_CURRENCIES].values():
        for pair in currency_details[commons_constants.CONFIG_CRYPTO_PAIRS]:
            if (
                symbol == symbol_util.parse_symbol(pair).base
                and currency_details.get(commons_constants.CONFIG_ENABLED_OPTION, True) is False
            ):
                return True
    return False



def get_symbols(config, enabled_only) -> list:
    if commons_constants.CONFIG_CRYPTO_CURRENCIES in config \
            and isinstance(config[commons_constants.CONFIG_CRYPTO_CURRENCIES], dict):
        return [
            symbol
            for currency, crypto_currency_data in config[commons_constants.CONFIG_CRYPTO_CURRENCIES].items()
            if not enabled_only or is_currency_enabled(config, currency, True)
            for symbol in crypto_currency_data.get(commons_constants.CONFIG_CRYPTO_PAIRS, [])
            if symbol != commons_constants.CONFIG_SYMBOLS_WILDCARD[0]
        ]
    return []


def get_symbol_trading_type(symbol) -> str:
    parsed_symbol = symbol_util.parse_symbol(symbol)
    if parsed_symbol.is_spot():
        return trading_enums.ExchangeTypes.SPOT.value
    elif parsed_symbol.is_perpetual_future():
        if parsed_symbol.is_linear():
            return trading_enums.FutureContractType.LINEAR_PERPETUAL.value
        if parsed_symbol.is_inverse():
            return trading_enums.FutureContractType.INVERSE_PERPETUAL.value
    else:
        if parsed_symbol.is_linear():
            return trading_enums.FutureContractType.LINEAR_EXPIRABLE.value
        if parsed_symbol.is_inverse():
            return trading_enums.FutureContractType.INVERSE_EXPIRABLE.value


def get_symbol_types_counts(config, enabled_only) -> dict:
    enabled_symbols = get_symbols(config, enabled_only)
    return collections.Counter(
        get_symbol_trading_type(symbol) for symbol in enabled_symbols
    )


def get_all_currencies(config, enabled_only=False) -> set:
    currencies = set()
    for symbol in get_symbols(config, enabled_only):
        base, quote = symbol_util.parse_symbol(symbol).base_and_quote()
        currencies.add(base)
        if quote is not None:
            currencies.add(quote)
    return currencies


def get_pairs(config, currency, enabled_only=False) -> list:
    return [
        symbol
        for symbol in get_symbols(config, enabled_only)
        if currency in symbol_util.parse_symbol(symbol).base_and_quote()
    ]


def get_market_pair(config, currency, enabled_only=False) -> (str, bool):
    if commons_constants.CONFIG_TRADING in config:
        reference_market = get_reference_market(config)
        for symbol in get_symbols(config, enabled_only):
            symbol_currency, symbol_market = symbol_util.parse_symbol(symbol).base_and_quote()
            if currency == symbol_currency and reference_market == symbol_market:
                return symbol, False
            elif reference_market == symbol_currency and currency == symbol_market:
                return symbol, True
    return "", False


def get_reference_market(config) -> str:
    # The reference market is the currency unit of the calculated quantity value
    return config[commons_constants.CONFIG_TRADING].get(commons_constants.CONFIG_TRADER_REFERENCE_MARKET,
                                                        trading_constants.DEFAULT_REFERENCE_MARKET)


def get_traded_pairs_by_currency(config):
    return {
        currency: val[commons_constants.CONFIG_CRYPTO_PAIRS]
        for currency, val in config[commons_constants.CONFIG_CRYPTO_CURRENCIES].items()
        if commons_constants.CONFIG_CRYPTO_PAIRS in val
           and val[commons_constants.CONFIG_CRYPTO_PAIRS]
           and is_currency_enabled(config, currency, True)
    }


def get_current_bot_live_id(config):
    return config[commons_constants.CONFIG_TRADING].get(
        commons_constants.CONFIG_CURRENT_LIVE_ID,
        commons_constants.DEFAULT_CURRENT_LIVE_ID
    )
