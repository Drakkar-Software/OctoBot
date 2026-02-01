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

from octobot_backtesting.api import data_file_converters
from octobot_backtesting.api import data_file
from octobot_backtesting.api import importer
from octobot_backtesting.api import backtesting
from octobot_backtesting.api import exchange_data_collector
from octobot_backtesting.api import social_data_collector

from octobot_backtesting.api.data_file_converters import (
    convert_data_file,
)
from octobot_backtesting.api.data_file import (
    get_all_available_data_files,
    delete_data_file,
    get_file_description,
)
from octobot_backtesting.api.importer import (
    create_importer,
    get_available_data_types,
    get_data_file,
    get_data_file_from_importers,
    get_data_file_path,
    get_available_time_frames,
    get_available_symbols,
    get_data_timestamp_interval,
    get_all_ohlcvs,
    stop_importer,
)
from octobot_backtesting.api.backtesting import (
    set_time_updater_interval,
    set_iteration_timeout,
    get_importers,
    get_backtesting_current_time,
    get_backtesting_starting_time,
    get_backtesting_ending_time,
    register_backtesting_timestamp_whitelist,
    get_backtesting_timestamp_whitelist,
    is_backtesting_enabled,
    get_backtesting_data_files,
    get_backtesting_duration,
    create_and_init_backtest_data,
    get_preloaded_candles_manager,
    initialize_backtesting,
    initialize_independent_backtesting_config,
    get_backtesting_time_channel_name,
    modify_backtesting_timestamps,
    adapt_backtesting_channels,
    start_backtesting,
    stop_backtesting,
    stop_independent_backtesting,
)
from octobot_backtesting.api.exchange_data_collector import (
    exchange_historical_data_collector_factory,
    exchange_bot_snapshot_data_collector_factory,
    initialize_and_run_data_collector,
    stop_data_collector,
    is_data_collector_in_progress,
    get_data_collector_progress,
    is_data_collector_finished,
)
from octobot_backtesting.api.social_data_collector import (
    social_historical_data_collector_factory,
    social_live_data_collector_factory,
)

__all__ = [
    "convert_data_file",
    "get_all_available_data_files",
    "delete_data_file",
    "get_file_description",
    "create_importer",
    "get_available_data_types",
    "get_data_file",
    "get_data_file_from_importers",
    "get_data_file_path",
    "get_available_time_frames",
    "get_available_symbols",
    "get_data_timestamp_interval",
    "get_all_ohlcvs",
    "stop_importer",
    "set_time_updater_interval",
    "set_iteration_timeout",
    "get_importers",
    "get_backtesting_current_time",
    "get_backtesting_starting_time",
    "get_backtesting_ending_time",
    "register_backtesting_timestamp_whitelist",
    "get_backtesting_timestamp_whitelist",
    "is_backtesting_enabled",
    "get_backtesting_data_files",
    "get_backtesting_duration",
    "create_and_init_backtest_data",
    "get_preloaded_candles_manager",
    "initialize_backtesting",
    "initialize_independent_backtesting_config",
    "get_backtesting_time_channel_name",
    "modify_backtesting_timestamps",
    "adapt_backtesting_channels",
    "start_backtesting",
    "stop_backtesting",
    "stop_independent_backtesting",
    "exchange_historical_data_collector_factory",
    "exchange_bot_snapshot_data_collector_factory",
    "initialize_and_run_data_collector",
    "stop_data_collector",
    "is_data_collector_in_progress",
    "get_data_collector_progress",
    "is_data_collector_finished",
    "social_historical_data_collector_factory",
    "social_live_data_collector_factory",
]
