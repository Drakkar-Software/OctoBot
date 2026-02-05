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
import logging
import contextlib
import typing

import octobot_commons.profiles as commons_profiles
import octobot_commons.configuration as commons_configuration
import octobot_commons.logging as commons_logging
import octobot_commons.symbols as commons_symbols
import octobot_commons.list_util as list_util
import octobot_commons.enums as common_enums

import octobot_backtesting.backtest_data
import octobot_backtesting.api

import octobot_tentacles_manager.configuration

import octobot.backtesting.independent_backtesting
import octobot.backtesting.minimal_data_importer as minimal_data_importer

import octobot_trading.util.test_tools.exchange_data as exchange_data_import
import octobot_trading.api

import tentacles.Meta.Keywords.scripting_library as scripting_library


@contextlib.asynccontextmanager
async def init_and_run_backtesting(
    exchange_data: exchange_data_import.ExchangeData,
    profile_data: commons_profiles.ProfileData,
) -> typing.AsyncGenerator[octobot.backtesting.independent_backtesting.IndependentBacktesting, None]:
    """
    Initialize and run backtesting.
    Usage:
    async with init_and_run_backtesting(exchange_data, profile_data) as independent_backtesting:
        # use independent_backtesting to get backtesting results before it gets stopped
    """
    async with run_backtesting(
        exchange_data, 
        profile_data, 
        scripting_library.create_backtesting_config(profile_data, exchange_data),
        scripting_library.get_full_tentacles_setup_config(profile_data),
    ) as independent_backtesting:
        yield independent_backtesting


@contextlib.asynccontextmanager
async def run_backtesting(
    exchange_data: exchange_data_import.ExchangeData,
    profile_data: commons_profiles.ProfileData,
    backtesting_config: commons_configuration.Configuration,
    tentacles_config: octobot_tentacles_manager.configuration.TentaclesSetupConfiguration,
    enable_logs: bool = False,
) -> typing.AsyncGenerator[octobot.backtesting.independent_backtesting.IndependentBacktesting, None]:
    with octobot_tentacles_manager.configuration.local_get_config_proxy(scripting_library.empty_config_proxy):
        backtest_data = await _init_backtest_data(
            exchange_data, backtesting_config, tentacles_config
        )
        independent_backtesting = None
        try:
            with commons_logging.temporary_log_level(logging.INFO):
                independent_backtesting = _init_independent_backtesting(
                    exchange_data, profile_data, backtest_data, enable_logs=enable_logs
                )
                await independent_backtesting.initialize_and_run(log_errors=True)
                await independent_backtesting.join_backtesting_updater(None)
            # independent_backtesting.log_report()  # uncomment to debug
            yield independent_backtesting
        finally:
            if independent_backtesting is not None:
                with commons_logging.temporary_log_level(logging.INFO):
                    await independent_backtesting.clear_fetched_data()
                    await independent_backtesting.stop(memory_check=False, should_raise=False)


def _init_independent_backtesting(
    exchange_data: exchange_data_import.ExchangeData,
    profile_data: commons_profiles.ProfileData,
    backtest_data: octobot_backtesting.backtest_data.BacktestData,
    enable_logs: bool = False,
    services_config: typing.Optional[dict] = None,
) -> "octobot.backtesting.independent_backtesting.IndependentBacktesting":
    independent_backtesting = octobot.backtesting.independent_backtesting.IndependentBacktesting(
        backtest_data.config,
        backtest_data.tentacles_config,
        backtest_data.data_files,
        run_on_common_part_only=True,
        start_timestamp=None,
        end_timestamp=None,
        enable_logs=enable_logs,
        stop_when_finished=False,
        run_on_all_available_time_frames=False,
        enforce_total_databases_max_size_after_run=False,
        enable_storage=False,
        backtesting_data=backtest_data,
        config_by_tentacle={
            tentacle.name: tentacle.config
            for tentacle in profile_data.tentacles
        },
        services_config=services_config or {},
    )
    independent_backtesting.symbols_to_create_exchange_classes.update({
        exchange: [
            commons_symbols.parse_symbol(s)
            for s in list_util.deduplicate([
                market_details.symbol
                for market_details in exchange_data.markets
                if market_details.has_full_candles()
            ])
        ]
        for exchange in [exchange_data.exchange_details.name]   # TODO handle multi exchanges
    })
    return independent_backtesting


async def _init_backtest_data(
    exchange_data: exchange_data_import.ExchangeData,
    backtesting_config: commons_configuration.Configuration,
    tentacles_config: octobot_tentacles_manager.configuration.TentaclesSetupConfiguration,
) -> octobot_backtesting.backtest_data.BacktestData:
    backtest_data = await octobot_backtesting.api.create_and_init_backtest_data(
        [], backtesting_config.config, tentacles_config, True
    )
    backtest_data.use_cached_markets = True
    await _init_importers(exchange_data, backtest_data)
    importer = next(iter(backtest_data.importers_by_data_file.values()))
    start_time, end_time = await importer.get_data_timestamp_interval()
    await _init_preloaded_candle_managers(exchange_data, backtest_data, start_time, end_time)
    return backtest_data


async def _init_importers(
    exchange_data: exchange_data_import.ExchangeData,
    backtest_data: octobot_backtesting.backtest_data.BacktestData,
):
    backtest_data.data_files = [f"simulated_{exchange_data.exchange_details.name}_file.data"]
    backtest_data.default_importer = minimal_data_importer.MinimalDataImporter # type: ignore
    await backtest_data.initialize()
    for importer in backtest_data.importers_by_data_file.values():
        importer.update_from_exchange_data(exchange_data) # type: ignore


async def _init_preloaded_candle_managers(
    exchange_data: exchange_data_import.ExchangeData,
    backtest_data: octobot_backtesting.backtest_data.BacktestData,
    start_time,
    end_time
):
    for exchange_details in [exchange_data.exchange_details]:
        for market_details in exchange_data.markets:
            if not market_details.has_full_candles():
                continue
            key = backtest_data._get_key(
                exchange_details.name, market_details.symbol, common_enums.TimeFrames(market_details.time_frame),
                start_time, end_time
            )
            backtest_data.preloaded_candle_managers[key] = await octobot_trading.api.create_preloaded_candles_manager(
                market_details.get_formatted_candles()
            )
