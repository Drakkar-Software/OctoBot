#  Drakkar-Software OctoBot-Tentacles
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
import typing
import os
import sortedcontainers
import time

import octobot_commons
import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.configuration as commons_configuration
import octobot_commons.profiles as commons_profiles
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_commons.symbols
import octobot_commons.logging

import octobot_evaluators.constants as evaluators_constants

import octobot_tentacles_manager.api

import octobot_trading.constants as trading_constants
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_trading.util.config_util as config_util
import octobot_trading.api
import octobot_trading.enums

import octobot_tentacles_manager.api


import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading
import octobot_copy.enums as copy_enums
import tentacles.Meta.Keywords.scripting_library.errors as scr_errors
import tentacles.Meta.Keywords.scripting_library.constants as scr_constants
import tentacles.Meta.Keywords.scripting_library.configuration.tentacles_configuration as tentacles_configuration
import tentacles.Meta.Keywords.scripting_library.configuration.indexes_configuration as indexes_configuration




def minimal_profile_data() -> commons_profiles.ProfileData:
    return commons_profiles.ProfileData.from_dict({
        "profile_details": {"name": ""},
        "crypto_currencies": [],
        "exchanges": [],
        "trading": {"reference_market": common_constants.DEFAULT_REFERENCE_MARKET}
    })


def empty_config_proxy(*_, **__):
    return {}


def create_backtesting_config(
    profile_data: commons_profiles.ProfileData,
    exchange_data: exchange_data_import.ExchangeData,
) -> commons_configuration.Configuration:
    tentacles_config = octobot_tentacles_manager.api.get_full_tentacles_setup_config(profile_data)
    apply_leverage_config(profile_data)
    profile_data.exchanges = [] # clear exchange to avoid conflicts with backtesting exchanges
    return config_util.get_config(
        profile_data, exchange_data, tentacles_config, False, False, False
    )


def create_profile_data_from_tentacles_config_history(
    tentacles_config_by_time: dict[float, list[commons_profile_data.TentaclesData]], exchange: str, starting_funds: float
) -> commons_profiles.ProfileData:
    if not tentacles_config_by_time:
        raise ValueError("tentacles_config_by_time is empty")
    ordered_config = sortedcontainers.SortedDict(tentacles_config_by_time)
    first_config = next(iter(ordered_config.values()))
    if first_config[0].name == index_trading.IndexTradingMode.get_name():
        backtesting_start_time_delta = time.time() - next(iter(ordered_config))
        historical_config_by_time = {
            timestamp: indexes_configuration.create_index_config_from_tentacles_config(
                config, exchange, starting_funds, backtesting_start_time_delta
            )
            for timestamp, config in ordered_config.items()
        }
        master_config = next(iter(historical_config_by_time.values()))
        if len(historical_config_by_time) > 1:
            register_historical_configs(
                master_config, historical_config_by_time, 
                add_historical_trading_pairs_to_master_profile_data=True, 
                apply_master_tentacle_config_edits_to_historical_configs=False
            )
        return master_config
    else:
        # todo implement other trading modes if necessary
        raise ValueError(f"{first_config.name} config not implemented")



def register_historical_configs(
    master_profile_data: commons_profiles.ProfileData,
    historical_profile_data_by_time: dict[float, commons_profiles.ProfileData],
    add_historical_trading_pairs_to_master_profile_data: bool,
    apply_master_tentacle_config_edits_to_historical_configs: bool
):
    if add_historical_trading_pairs_to_master_profile_data:
        # 1. register every historical profile traded pairs in master profile
        if added_pairs := get_historical_added_config_trading_pairs(
            master_profile_data, historical_profile_data_by_time.values()
        ):
            add_traded_symbols(master_profile_data, added_pairs)

    # 2. register historical tentacles_config
    config_by_tentacle = master_profile_data.get_config_by_tentacle()
    for historical_time, historical_profile in historical_profile_data_by_time.items():
        historical_config_by_tentacle = historical_profile.get_config_by_tentacle()
        for tentacle, config in historical_config_by_tentacle.items():
            master_config = config_by_tentacle[tentacle]
            if config is not master_config:
                if apply_master_tentacle_config_edits_to_historical_configs:
                    try:
                        _apply_master_tentacle_config_edits_to_historical_config(tentacle, master_config, config)
                    except RuntimeError:
                        # tentacle not found, continue
                        _get_logger().error(f"Tentacle {tentacle} not found in available tentacles")
                commons_configuration.add_historical_tentacle_config(
                    master_config,
                    historical_time,
                    config,
                )


def _apply_master_tentacle_config_edits_to_historical_config(tentacle: str, master_config: dict, historical_config: dict):
    if updatable_keys := tentacles_configuration.get_config_history_propagated_tentacles_config_keys(tentacle):
        for key in updatable_keys:
            if key in master_config:
                historical_config[key] = master_config[key]


def get_historical_added_config_trading_pairs(
    master_profile_data: commons_profiles.ProfileData, 
    historical_profile_data: typing.Optional[typing.Iterable[commons_profiles.ProfileData]]
) -> list[str]:
    if historical_profile_data:
        historical_pairs = [
            pair
            for historical_profile in historical_profile_data
            for pair in historical_profile.get_traded_symbols()
        ]
    else:
        historical_pairs = get_historical_traded_pairs(master_profile_data)
    registered_pairs = master_profile_data.get_traded_symbols()
    added_pairs = []
    for pair in historical_pairs:
        if pair not in registered_pairs:
            registered_pairs.append(pair)
            added_pairs.append(pair)
    return added_pairs


def get_historical_traded_pairs(
    profile_data: commons_profiles.ProfileData
) -> typing.Iterable[str]:
    trading_mode = get_trading_mode(profile_data)
    trading_mode_config = _get_trading_mode_config(profile_data)
    historical_trading_mode_configs = commons_configuration.get_historical_tentacle_configs(
        trading_mode_config, 0, time.time()
    )
    if trading_mode == index_trading.IndexTradingMode.get_name():
        return _get_historical_index_trading_pairs(profile_data, historical_trading_mode_configs) #todo
    else:
        raise NotImplementedError(f"Trading mode {trading_mode} not implemented")



def _get_historical_index_trading_pairs(
    profile_data: commons_profiles.ProfileData, historical_trading_mode_configs: typing.Iterable[dict]
) -> typing.Iterable[str]:
    historical_assets = []
    latest_config_assets = set(
        asset[copy_enums.DistributionKeys.NAME]
        for asset in _get_trading_mode_config(profile_data)[
            index_trading.IndexTradingModeProducer.INDEX_CONTENT
        ]
    )
    for historical_trading_mode_config in historical_trading_mode_configs:
        for asset in historical_trading_mode_config[index_trading.IndexTradingModeProducer.INDEX_CONTENT]:
            historical_asset = asset[copy_enums.DistributionKeys.NAME]
            if historical_asset not in historical_assets and historical_asset not in latest_config_assets:
                historical_assets.append(historical_asset)
    return [
        octobot_commons.symbols.merge_currencies(asset, profile_data.trading.reference_market)
        for asset in historical_assets
    ]


def add_traded_symbols(
    profile_data: commons_profiles.ProfileData,
    added_symbols: typing.Iterable[str]
):
    traded_symbols = profile_data.get_traded_symbols()
    to_add_symbols = [
        symbol
        for symbol in added_symbols
        if symbol not in traded_symbols
    ]
    if to_add_symbols:
        _get_logger().info(f"Adding {to_add_symbols} to profile data traded pairs.")
        expand_traded_pairs_into_currencies(profile_data, to_add_symbols)


def expand_traded_pairs_into_currencies(profile_data, pairs: list[str]):
    for pair in pairs:
        profile_data.crypto_currencies.append(
            commons_profile_data.CryptoCurrencyData(
                trading_pairs=[pair],
                name=pair,
                enabled=True
            )
        )


def filter_out_missing_symbols(profile_data: commons_profiles.ProfileData, available_symbols: list[str]) -> list[str]:
    traded_pairs = profile_data.get_traded_symbols()
    removed_symbols = [symbol for symbol in traded_pairs if symbol not in available_symbols]
    if removed_symbols:
        profile_data.crypto_currencies = []
        add_traded_symbols(
            profile_data,
            [pair for pair in traded_pairs if pair not in removed_symbols]
        )
    return removed_symbols


def get_readonly_exchange_auth_details(exchange_internal_name: str) -> exchange_data_import.ExchangeAuthDetails:
    return exchange_data_import.ExchangeAuthDetails(
        api_key=_get_readonly_exchange_credential_from_env(exchange_internal_name, "KEY", False),
        api_secret=_get_readonly_exchange_credential_from_env(exchange_internal_name, "SECRET", False),
        api_password=_get_readonly_exchange_credential_from_env(exchange_internal_name, "PASSWORD", True),
        sandboxed=False,
        broker_enabled=False,
    )


def _get_readonly_exchange_credential_from_env(exchange_name, cred_suffix, allow_missing):
    # for coinbase: COINBASE_READ_ONLY_KEY, COINBASE_READ_ONLY_SECRET, COINBASE_READ_PASSWORD
    if cred := os.getenv(f"{exchange_name}_READ_ONLY_{cred_suffix}".upper(), None):
        return commons_configuration.encrypt(cred).decode()
    if allow_missing:
        return None
    raise scr_errors.MissingReadOnlyExchangeCredentialsError(
        f"{exchange_name} read only credentials are missing"
    )


def get_required_candles_count(profile_data: commons_profiles.ProfileData, min_candles_count: int) -> int:
    for tentacle_config in profile_data.tentacles:
        if common_constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT in tentacle_config.config:
            return max(
                tentacle_config.config[common_constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT],
                min_candles_count
            )
    return min_candles_count


def update_position_levarage(
    position: exchange_data_import.PositionDetails, updated_contracts_by_symbol: dict
):
    leverage = float(
        updated_contracts_by_symbol[
            position.contract[octobot_trading.enums.ExchangeConstantsMarginContractColumns.PAIR.value]
        ].current_leverage
    )
    position.contract[octobot_trading.enums.ExchangeConstantsMarginContractColumns.CURRENT_LEVERAGE.value] = leverage
    position.position[octobot_trading.enums.ExchangeConstantsPositionColumns.LEVERAGE.value] = leverage


def merge_profile_data(
    profile_data: commons_profiles.ProfileData,
    previous_profile_data: commons_profiles.ProfileData,
) -> commons_profiles.ProfileData:
    # previous config crypto currencies are merged
    current_traded_pairs = set(profile_data.get_traded_symbols())
    for currency_data in previous_profile_data.crypto_currencies:
        for previous_traded_pair in currency_data.trading_pairs:
            to_add_pairs = set()
            if previous_traded_pair not in current_traded_pairs:
                # add pair
                to_add_pairs.add(previous_traded_pair)
            parsed_symbol = octobot_commons.symbols.parse_symbol(previous_traded_pair)
            if parsed_symbol.quote != profile_data.trading.reference_market:
                # reference market changed: also include the base of this pair within the traded pairs
                ref_market_pair = octobot_commons.symbols.merge_currencies(
                    parsed_symbol.base, profile_data.trading.reference_market
                )
                if ref_market_pair not in current_traded_pairs:
                    to_add_pairs.add(ref_market_pair)
            for traded_pair in to_add_pairs:
                _get_logger().info(
                    f"Profile data merge: including previous config {currency_data} currency into current profile data"
                )
                expand_traded_pairs_into_currencies(profile_data, [traded_pair])
                current_traded_pairs.add(traded_pair)
    return profile_data



def apply_leverage_config(profile_data: commons_profiles.ProfileData):
    if leverage := profile_data.future_exchange_data.default_leverage:
        trading_mode_config = _get_trading_mode_config(profile_data)
        apply_leverage_config_to_trading_mode_config_if_necessary(trading_mode_config, leverage)


def apply_leverage_config_to_trading_mode_config_if_necessary(trading_mode_config: dict, leverage: float):
    if trading_constants.CONFIG_LEVERAGE not in trading_mode_config:
        trading_mode_config[trading_constants.CONFIG_LEVERAGE] = leverage

def _get_trading_mode_config(profile_data: commons_profiles.ProfileData):
    trading_mode = get_trading_mode(profile_data)
    config_by_tentacle = profile_data.get_config_by_tentacle()
    if trading_mode in config_by_tentacle:
        return config_by_tentacle[trading_mode]
    raise KeyError(f"No trading mode config found in {list(config_by_tentacle)} tentacles config")


def get_trading_mode(profile_data: commons_profiles.ProfileData) -> typing.Optional[str]:
    for tentacle_name in profile_data.get_config_by_tentacle():
        if tentacles_configuration.is_trading_mode_tentacle(tentacle_name):
            return tentacle_name
    return None


def get_traded_coins(
    profile_data: commons_profiles.ProfileData,
    include_stablecoins: bool,
) -> list[str]:
    # return an ordered list of:
    # 1. reference market
    # 2. traded assets
    # 3. stablecoins if include_stablecoins is True
    coins = [profile_data.trading.reference_market, ]
    for symbol in profile_data.get_traded_symbols():
        base, quote = octobot_commons.symbols.parse_symbol(symbol).base_and_quote()
        if base not in coins:
            coins.append(base)
        if quote not in coins:
            coins.append(quote)
    if include_stablecoins:
        coins.extend(tuple(
            coin
            for coin in common_constants.USD_LIKE_AND_FIAT_COINS
            if coin not in coins
        ))
    return coins


def get_time_frames(
    profile_data: commons_profiles.ProfileData, for_historical_data=False
) -> list[str]:
    for config in profile_data.get_config_by_tentacle().values():
        if evaluators_constants.STRATEGIES_REQUIRED_TIME_FRAME in config:
            return config[evaluators_constants.STRATEGIES_REQUIRED_TIME_FRAME]
    return [_get_default_time_frame(profile_data, for_historical_data)]


def _get_default_time_frame(profile_data: commons_profiles.ProfileData, for_historical_data: bool):
    if not for_historical_data:
        # always use DEFAULT_TIMEFRAME when focusing on historical data
        return scr_constants.DEFAULT_TIMEFRAME.value
    return _get_historical_default_time_frame(profile_data)


def _get_historical_default_time_frame(profile_data: commons_profiles.ProfileData):
    if time_frame := get_default_historical_time_frame(profile_data):
        return time_frame.value
    # fallback to default timeframe
    return scr_constants.DEFAULT_TIMEFRAME.value


def requires_price_update_timeframe(profile_data: commons_profiles.ProfileData) -> bool:
    if trading_mode := get_trading_mode(profile_data):
        return octobot_tentacles_manager.api.get_tentacle_class_from_string(
            trading_mode
        ).use_backtesting_accurate_price_update()
    return True


def get_default_historical_time_frame(profile_data: commons_profiles.ProfileData) -> typing.Optional[common_enums.TimeFrames]:
    if trading_mode := get_trading_mode(profile_data):
        return octobot_tentacles_manager.api.get_tentacle_class_from_string(
            trading_mode
        ).get_default_historical_time_frame()
    return None


def can_convert_ref_market_to_usd_like(
    exchange_data: exchange_data_import.ExchangeData,
    profile_data: commons_profiles.ProfileData
):
    return can_convert_ref_market_to_usd_like_from_symbols(
        profile_data.trading.reference_market,
        [market.symbol for market in exchange_data.markets]
    )

def can_convert_ref_market_to_usd_like_from_symbols(
    reference_market: str,
    symbols: list[str]
):
    if octobot_trading.api.is_usd_like_coin(reference_market):
        return True
    for symbol in symbols:
        if (
            reference_market in octobot_commons.symbols.parse_symbol(symbol).base_and_quote()
            and octobot_trading.api.can_convert_symbol_to_usd_like(symbol)
        ):
            return True
    return False


def set_backtesting_portfolio(profile_data, exchange_data):
    exchange_data.portfolio_details.content = {
        asset: {
            common_constants.PORTFOLIO_AVAILABLE: value,
            common_constants.PORTFOLIO_TOTAL: value
        }
        for asset, value in profile_data.backtesting_context.starting_portfolio.items()
    }
    _get_logger().info(
        f"Applied {profile_data.profile_details.name} backtesting starting "
        f"portfolio: {profile_data.backtesting_context.starting_portfolio}"
    )


def get_oldest_historical_config_symbols_and_time(profile_data: commons_profiles.ProfileData, default) -> (list, float):
    first_historical_config_time = _get_first_historical_config_time(profile_data, default)
    if first_historical_config_time == default:
        base_traded_symbols = profile_data.get_traded_symbols()
        return base_traded_symbols, base_traded_symbols, default
    first_traded_symbols = _get_all_tentacles_configured_traded_symbols(profile_data, first_historical_config_time)
    last_traded_symbols = _get_all_tentacles_configured_traded_symbols(profile_data, None)
    return list(first_traded_symbols), list(last_traded_symbols), first_historical_config_time


def _get_all_tentacles_configured_traded_symbols(
    profile_data: commons_profiles.ProfileData, first_historical_config_time: typing.Optional[float]
) -> set:
    traded_symbols = set()
    tentacles_config = profile_data.get_config_by_tentacle()
    for tentacle, tentacle_config in tentacles_config.items():
        if first_historical_config_time is None:
            config = tentacle_config
        else:
            try:
                config = commons_configuration.get_historical_tentacle_config(
                    tentacle_config, first_historical_config_time
                )
            except KeyError as err:
                if tentacles_configuration.is_exchange_tentacle(tentacle):
                    # exchange tentacles (like HollaEx exchanges) don't have historical configuration: this is normal
                    pass
                else:
                    raise scr_errors.InvalidProfileError(f"{tentacle} tentacle config is invalid: {err}")
        traded_symbols.update(get_tentacle_config_traded_symbols(
            tentacle, config, profile_data.trading.reference_market
        ))
    return traded_symbols


def _get_first_historical_config_time(profile_data: commons_profiles.ProfileData, default) -> float:
    tentacles_config = profile_data.get_config_by_tentacle()
    oldest_config_times = []
    for tentacle, config in tentacles_config.items():
        try:
            oldest_config_times.append(
                commons_configuration.get_oldest_historical_tentacle_config_time(
                    config
                )
            )
        except ValueError:
            # no historical config
            pass
    if oldest_config_times:
        # return the most recent of the oldest configurations
        return max(oldest_config_times)
    return default


def get_tentacle_config_traded_symbols(tentacle: str, config: dict, reference_market: str) -> set:
    tentacle_class = octobot_tentacles_manager.api.get_tentacle_class_from_string(tentacle)
    try:
        return set(tentacle_class.get_tentacle_config_traded_symbols(config, reference_market))
    except NotImplementedError as err:
        if tentacles_configuration.is_exchange_tentacle(tentacle):
            # exchange tentacles don't implement get_tentacle_config_traded_symbols, this is normal
            pass
        else:
            _get_logger().warning(
                f"Trying to get tentacle config historical traded symbols for {tentacle}: {err}"
            )
        return set()


def _get_logger():
    return octobot_commons.logging.get_logger("ScriptedProfileData")
