#  Drakkar-Software OctoBot-Backtesting
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
import time

import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.logging as logging
import octobot_commons.time_frame_manager as time_frame_manager

import octobot_backtesting.api as api
import octobot_backtesting.errors as errors
import octobot_backtesting.backtesting as backtesting_class
import octobot_backtesting.backtest_data as backtest_data
import octobot_backtesting.constants as constants


LOGGER_NAME = "BacktestingAPI"


async def initialize_backtesting(config, exchange_ids, matrix_id, data_files,
                                 importers_by_data_file=None, backtest_data=None,
                                 bot_id=None) -> backtesting_class.Backtesting:
    backtesting_instance = backtesting_class.Backtesting(config=config,
                                                         exchange_ids=exchange_ids,
                                                         matrix_id=matrix_id,
                                                         backtesting_files=data_files,
                                                         importers_by_data_file=importers_by_data_file,
                                                         backtest_data=backtest_data,
                                                         bot_id=bot_id)
    await backtesting_instance.create_importers()
    await backtesting_instance.initialize()

    if not backtesting_instance.importers:
        raise ValueError("No importers created: did you enter the backtesting file(s) to use ?")

    return backtesting_instance


async def initialize_independent_backtesting_config(independent_backtesting) -> dict:
    return await independent_backtesting.initialize_config()


def get_backtesting_time_channel_name(backtesting) -> str:
    return backtesting.get_time_chan_name()


async def modify_backtesting_timestamps(backtesting, set_timestamp=None,
                                        minimum_timestamp=None, maximum_timestamp=None) -> None:
    await backtesting.time_updater.modify(set_timestamp=set_timestamp,
                                          minimum_timestamp=minimum_timestamp,
                                          maximum_timestamp=maximum_timestamp)


async def _get_min_max_timestamps(importers, run_on_common_part_only, start_timestamp, end_timestamp,
                                  min_time_frame_to_consider, max_time_frame_to_consider):
    # set mininmum and maximum timestamp according to all importers data
    try:
        short_tf_timestamps = [await api.get_data_timestamp_interval(importer, min_time_frame_to_consider)
                               for importer in importers]  # [(min, max) ... ]
        large_tf_timestamps = [await api.get_data_timestamp_interval(importer, max_time_frame_to_consider)
                               for importer in importers]  # [(min, max) ... ]
    except errors.MissingTimeFrame as e:
        raise RuntimeError(f"Impossible to start backtesting on this configuration: {e}")
    min_timestamps = [timestamp[0] for timestamp in short_tf_timestamps]
    max_timestamps = [timestamp[1] for timestamp in short_tf_timestamps]

    min_timestamp = max(min_timestamps) if run_on_common_part_only else min(min_timestamps)
    max_timestamp = min(max_timestamps) if run_on_common_part_only else max(max_timestamps)

    large_min_timestamps = [timestamp[0] for timestamp in large_tf_timestamps]
    min_large_timestamp = max(large_min_timestamps) if run_on_common_part_only else min(large_min_timestamps)

    # set min timestamp where we have data in the largest candle to avoid starting with missing large candles data
    min_timestamp = max(min_timestamp, min_large_timestamp)

    if min_timestamp > max_timestamp:
        raise RuntimeError(f"No candle data to run backtesting on in this time window: starting at: {min_timestamp} "
                           f"and ending at: {max_timestamp}")
    if start_timestamp is not None and end_timestamp is not None and \
            start_timestamp > end_timestamp:
        raise RuntimeError(f"No candle data to run backtesting on in this time window: starting at: {start_timestamp} "
                           f"and ending at: {end_timestamp}")

    time_frame_sec = common_enums.TimeFramesMinutes[min_time_frame_to_consider] * common_constants.MINUTE_TO_SECONDS
    if start_timestamp is not None:
        # Adapt start and end timestamp to start exactly at the top of the 1st available candle
        # This avoids backtesting to run from mid candle time to mid candle time.
        # Adapt start timestamp
        start_timestamp = start_timestamp + (time_frame_sec - start_timestamp % time_frame_sec)

        if min_timestamp <= start_timestamp < (end_timestamp if end_timestamp else max_timestamp):
            min_timestamp = start_timestamp
        else:
            logging.get_logger(LOGGER_NAME).warning(f"Can't set the minimum timestamp to {start_timestamp}. "
                                                         f"The minimum available({min_timestamp}) will be used instead.")
    if end_timestamp is not None:
        # Adapt end timestamp
        end_timestamp = end_timestamp - (end_timestamp % time_frame_sec)

        if max_timestamp >= end_timestamp > start_timestamp if start_timestamp else min_timestamp:
            max_timestamp = end_timestamp
        else:
            logging.get_logger(LOGGER_NAME).warning(f"Can't set the maximum timestamp to {end_timestamp}. "
                                                         f"The maximum available({max_timestamp}) will be used instead.")
    return min_timestamp, max_timestamp


async def adapt_backtesting_channels(backtesting, config, importer_class,
                                     run_on_common_part_only=True,
                                     start_timestamp=None, end_timestamp=None):
    importers = backtesting.get_importers(importer_class)
    if not importers:
        raise RuntimeError("No exchange importer has been found for this data file, backtesting can't start.")
    sorted_time_frames = time_frame_manager.sort_time_frames(time_frame_manager.get_config_time_frame(config))
    sorted_available_time_frames = time_frame_manager.sort_time_frames(api.get_available_time_frames(importers[0]))
    min_available_time_frame = sorted_available_time_frames[0]
    if not sorted_time_frames or (
        backtesting.use_accurate_price_time_frame() and sorted_time_frames[0] != min_available_time_frame
    ):
        # use min available timeframe as default if no timeframe is enabled or if add min available timeframe
        # if not already in handled time frames
        sorted_time_frames.insert(0, min_available_time_frame)
    min_time_frame_to_consider = sorted_time_frames[0]
    max_time_frame_to_consider = sorted_time_frames[-1]
    _ensure_extra_time_frames(min_time_frame_to_consider, config)
    min_timestamp, max_timestamp = await _get_min_max_timestamps(importers, run_on_common_part_only,
                                                                 start_timestamp, end_timestamp,
                                                                 min_time_frame_to_consider, max_time_frame_to_consider)

    await modify_backtesting_timestamps(
        backtesting,
        minimum_timestamp=int(min_timestamp),
        maximum_timestamp=int(max_timestamp))
    try:
        import octobot_trading.api as exchange_api

        if exchange_api.has_only_ohlcv(importers):
            set_time_updater_interval(backtesting,
                                      common_enums.TimeFramesMinutes[min_time_frame_to_consider] *
                                      common_constants.MINUTE_TO_SECONDS)
    except ImportError:
        logging.get_logger(LOGGER_NAME).error("requires OctoBot-Trading package installed")
    return min_timestamp, max_timestamp


def _ensure_extra_time_frames(min_time_frame_to_consider, config):
    min_tf_minutes = common_enums.TimeFramesMinutes[min_time_frame_to_consider]
    for required_extra_time_frame in config.get(common_constants.CONFIG_REQUIRED_EXTRA_TIMEFRAMES, []):
        if common_enums.TimeFramesMinutes[common_enums.TimeFrames(required_extra_time_frame)] < min_tf_minutes:
            raise errors.MissingTimeFrame(
                f"Missing required (or lower) time frame in data file: {required_extra_time_frame}"
            )


def set_time_updater_interval(backtesting, interval_in_seconds):
    backtesting.time_manager.time_interval = interval_in_seconds


def set_iteration_timeout(backtesting, iteration_timeout_in_seconds):
    backtesting.time_updater.channels_manager.refresh_timeout = iteration_timeout_in_seconds


async def start_backtesting(backtesting) -> None:
    await backtesting.start_time_updater()


async def stop_backtesting(backtesting) -> None:
    await backtesting.stop()


async def stop_independent_backtesting(independent_backtesting) -> None:
    await independent_backtesting.stop()


def get_importers(backtesting) -> list:
    return backtesting.importers


def get_backtesting_current_time(backtesting) -> float:
    return backtesting.time_manager.current_timestamp


def get_backtesting_starting_time(backtesting) -> float:
    return backtesting.time_manager.starting_timestamp


def get_backtesting_ending_time(backtesting) -> float:
    return backtesting.time_manager.finishing_timestamp


def register_backtesting_timestamp_whitelist(backtesting, timestamps, check_callback, append_to_whitelist=False):
    backtesting.time_manager.register_timestamp_whitelist(timestamps, check_callback,
                                                          append_to_whitelist=append_to_whitelist)


def get_backtesting_timestamp_whitelist(backtesting) -> list:
    return backtesting.time_manager.timestamps_whitelist


def is_backtesting_enabled(config) -> bool:
    return constants.CONFIG_BACKTESTING in config \
           and common_constants.CONFIG_ENABLED_OPTION in config[constants.CONFIG_BACKTESTING] \
           and config[constants.CONFIG_BACKTESTING][common_constants.CONFIG_ENABLED_OPTION]


def get_backtesting_data_files(config) -> list:
    return config.get(constants.CONFIG_BACKTESTING, {}).get(constants.CONFIG_BACKTESTING_DATA_FILES, [])


def get_backtesting_duration(backtesting) -> float:
    if backtesting.time_updater.simulation_duration > 0:
        return backtesting.time_updater.simulation_duration
    return time.time() - backtesting.time_updater.starting_time


async def create_and_init_backtest_data(data_files, config, tentacles_config, use_accurate_price_time_frame) \
        -> backtest_data.BacktestData:
    backtest_data_inst = backtest_data.BacktestData(data_files, config, tentacles_config, use_accurate_price_time_frame)
    await backtest_data_inst.initialize()
    return backtest_data_inst


async def get_preloaded_candles_manager(backtesting, exchange, symbol, time_frame):
    if backtesting.backtest_data is None:
        return None 
    return await backtesting.backtest_data.get_preloaded_candles_manager(
        exchange, symbol, time_frame,
        get_backtesting_starting_time(backtesting), get_backtesting_ending_time(backtesting)
    )
