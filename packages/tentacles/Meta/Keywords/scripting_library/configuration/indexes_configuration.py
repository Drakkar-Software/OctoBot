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
import octobot_commons
import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.profiles as commons_profiles
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_commons.symbols

import octobot_evaluators.constants as evaluators_constants

import octobot_trading.constants as trading_constants

import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading
import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution
import tentacles.Meta.Keywords.scripting_library.configuration.exchanges_configuration as exchanges_configuration


def create_index_config_from_tentacles_config(
    tentacles_config: list[commons_profile_data.TentaclesData], exchange: str,
    starting_funds: float, backtesting_start_time_delta: float
) -> commons_profiles.ProfileData:
    trading_mode_config = tentacles_config[0].config
    distribution = trading_mode_config[index_trading.IndexTradingModeProducer.INDEX_CONTENT]
    reference_market = exchanges_configuration.get_default_exchange_reference_market(exchange)
    # replace USD by reference market
    for element in distribution:
        if element[index_distribution.DISTRIBUTION_NAME] == "USD":
            element[index_distribution.DISTRIBUTION_NAME] = reference_market
    coins_by_symbol = {
        element[index_distribution.DISTRIBUTION_NAME]: element[index_distribution.DISTRIBUTION_NAME]
        for element in distribution
    }
    rebalance_cap = trading_mode_config[index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT]
    min_funds = starting_funds / 10
    selected_rebalance_trigger_profile = trading_mode_config.get(index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE, None)
    rebalance_trigger_profiles = trading_mode_config.get(index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES, None)
    profile_data_dict = generate_index_config(
        distribution, rebalance_cap, selected_rebalance_trigger_profile, rebalance_trigger_profiles, reference_market, exchange,
        min_funds, coins_by_symbol, False, backtesting_start_time_delta
    )
    return commons_profiles.ProfileData.from_dict(profile_data_dict)


def generate_index_config(
    distribution: typing.List, rebalance_cap: float, 
    selected_rebalance_trigger_profile: typing.Optional[str], rebalance_trigger_profiles: typing.Optional[list[dict]], 
    reference_market: str,
    exchange: str, min_funds: float, coins_by_symbol: dict[str, str], disabled_backtesting: bool,
    backtesting_start_time_delta: float
) -> dict:
    profile_details = commons_profile_data.ProfileDetailsData(name="serverless")
    trading = commons_profile_data.TradingData(
        reference_market=reference_market, risk=0.5
    )
    config_exchanges = [commons_profile_data.ExchangeData(
        internal_name=exchange, exchange_type=common_constants.CONFIG_EXCHANGE_SPOT
    )]
    currencies = [
        commons_profile_data.CryptoCurrencyData(
            [octobot_commons.symbols.merge_currencies(element[index_distribution.DISTRIBUTION_NAME], reference_market)],
            coins_by_symbol.get(
                element[index_distribution.DISTRIBUTION_NAME],
                element[index_distribution.DISTRIBUTION_NAME]
            )
        )
        for element in distribution
        if element[index_distribution.DISTRIBUTION_NAME] != reference_market
    ]
    trader = commons_profile_data.TraderData(enabled=True)
    trader_simulator = commons_profile_data.TraderSimulatorData()
    tentacles = [
        commons_profile_data.TentaclesData(
            index_trading.IndexTradingMode.get_name(), _get_index_trading_config(
                distribution, rebalance_cap, selected_rebalance_trigger_profile, rebalance_trigger_profiles
            )
        )
    ]
    backtesting = generate_index_backtesting_config(
        exchange, reference_market, min_funds, disabled_backtesting, backtesting_start_time_delta
    )
    base_config = commons_profiles.ProfileData(
        profile_details, currencies, trading, config_exchanges, commons_profile_data.FutureExchangeData(),
        trader, trader_simulator, tentacles, backtesting
    )
    return base_config.to_dict(include_default_values=False)


def generate_index_backtesting_config(
    exchange: str, reference_market: str, min_funds: float, disabled_backtesting: bool, start_time_delta: float
) -> commons_profile_data.BacktestingContext:
    return commons_profile_data.BacktestingContext(
        exchanges=[] if disabled_backtesting else [exchange],
        start_time_delta=start_time_delta,
        starting_portfolio={
            reference_market: min_funds * 10    # make sure there is always enough funds even if the market crashes
        }
    )


def _get_index_trading_config(
    distribution: typing.List, 
    rebalance_cap: float, 
    selected_rebalance_trigger_profile: typing.Optional[str], 
    rebalance_trigger_profiles: typing.Optional[list[dict]]
):
    return {
        trading_constants.TRADING_MODE_REQUIRED_STRATEGIES: [],
        index_trading.IndexTradingModeProducer.REFRESH_INTERVAL: 1,
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT: rebalance_cap,
        index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE: selected_rebalance_trigger_profile,
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES: rebalance_trigger_profiles,
        index_trading.IndexTradingModeProducer.SYNCHRONIZATION_POLICY: index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE.value,
        index_trading.IndexTradingModeProducer.SELL_UNINDEXED_TRADED_COINS: True,
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: distribution,
        evaluators_constants.STRATEGIES_REQUIRED_TIME_FRAME: [common_enums.TimeFrames.ONE_DAY.value],
    }
