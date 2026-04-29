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
import typing
import collections
import logging

import octobot_commons.constants as commons_constants
import octobot_commons.enums as common_enums
import octobot_commons.configuration as commons_configuration
import octobot_commons.profiles as commons_profiles
import octobot_commons.symbols as symbol_util
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges

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
    raise ValueError(f"Invalid symbol: {symbol}")


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


def get_formatted_portfolio(portfolio: dict):
    for asset in portfolio.values():
        if commons_constants.PORTFOLIO_AVAILABLE not in asset:
            asset[commons_constants.PORTFOLIO_AVAILABLE] = asset[trading_constants.CONFIG_PORTFOLIO_FREE]
    return portfolio


def get_exchange_config(
    exchange_data: "octobot_trading.exchanges.ExchangeData",
    tentacles_setup_config,
    exchange_config_by_exchange: typing.Optional[dict[str, dict]],
    auth: bool
):
    auth_details = exchange_data.auth_details
    if not auth:
        import octobot_trading.exchanges.util # avoid circular import
        always_auth = octobot_trading.exchanges.util.is_auth_required_exchanges(exchange_data, tentacles_setup_config, exchange_config_by_exchange)
        if always_auth:
            # force authentication when required on exchanges
            auth = True

    exchange_config = {
        commons_constants.CONFIG_EXCHANGE_KEY: auth_details.api_key if auth else None,
        commons_constants.CONFIG_EXCHANGE_SECRET: auth_details.api_secret if auth else None,
        commons_constants.CONFIG_EXCHANGE_PASSWORD: auth_details.api_password if auth else None,
        commons_constants.CONFIG_EXCHANGE_ACCESS_TOKEN: auth_details.access_token if auth else None,
        commons_constants.CONFIG_EXCHANGE_TYPE: auth_details.exchange_type or commons_constants.CONFIG_EXCHANGE_SPOT,
    }
    exchange_config[commons_constants.CONFIG_EXCHANGE_SANDBOXED] = auth_details.sandboxed
    return exchange_config


def get_config(
    profile_data: commons_profiles.ProfileData,
    exchange_data: "octobot_trading.exchanges.ExchangeData",
    tentacles_setup_config,
    auth: bool,
    ignore_symbols_in_exchange_init: bool,
    use_exchange_data_portfolio: bool,
) -> commons_configuration.Configuration:
    config = commons_configuration.Configuration(None, None)
    config.logger.logger.setLevel(logging.WARNING)  # disable "using XYZ profile." log
    config.config = {}
    initial_backtesting_context = profile_data.backtesting_context
    # always use exchange data on real trading
    # use exchange data on simulated only when exchange_data.portfolio_details.content is available
    if use_exchange_data_portfolio and (
        not profile_data.trader_simulator.enabled or exchange_data.portfolio_details.content
    ):
        profile_data.trader_simulator.starting_portfolio = get_formatted_portfolio(
            exchange_data.portfolio_details.content
        )
        # do not allow using backtesting context when using exchange data portfolio
        profile_data.backtesting_context = None # type: ignore
    profile = profile_data.to_profile(None)
    profile_data.backtesting_context = initial_backtesting_context
    config.profile_by_id[profile.profile_id] = profile
    config.select_profile(profile.profile_id)
    config.config[commons_constants.CONFIG_EXCHANGES][exchange_data.exchange_details.name] = get_exchange_config(
        exchange_data, tentacles_setup_config, profile_data.get_config_by_tentacle(), auth
    )
    if ignore_symbols_in_exchange_init:
        config.config[commons_constants.CONFIG_CRYPTO_CURRENCIES] = {}
    config.config[commons_constants.CONFIG_TIME_FRAME] = time_frame_manager.sort_time_frames(list(set(
        common_enums.TimeFrames(market.time_frame)
        for market in exchange_data.markets
    )))
    return config
