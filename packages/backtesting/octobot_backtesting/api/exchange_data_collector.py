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
import octobot_backtesting.collectors as collectors
import octobot_commons.tentacles_management as tentacles_management


def exchange_historical_data_collector_factory(exchange_name,
                                               exchange_type,
                                               tentacles_setup_config,
                                               symbols,
                                               time_frames=None,
                                               start_timestamp=None,
                                               end_timestamp=None,
                                               config=None):
    return _exchange_collector_factory(collectors.AbstractExchangeHistoryCollector,
                                       exchange_name,
                                       exchange_type,
                                       tentacles_setup_config,
                                       symbols,
                                       time_frames,
                                       start_timestamp,
                                       end_timestamp,
                                       config)


def exchange_bot_snapshot_data_collector_factory(exchange_name,
                                                 tentacles_setup_config,
                                                 symbols,
                                                 exchange_id,
                                                 time_frames=None,
                                                 start_timestamp=None,
                                                 end_timestamp=None,
                                                 config=None):
    collector = _exchange_collector_factory(collectors.AbstractExchangeBotSnapshotCollector,
                                            exchange_name,
                                            None,
                                            tentacles_setup_config,
                                            symbols,
                                            time_frames,
                                            start_timestamp,
                                            end_timestamp,
                                            config)
    collector.register_exchange_id(exchange_id)
    return collector


def _exchange_collector_factory(collector_parent_class, exchange_name, exchange_type, tentacles_setup_config, symbols,
                                time_frames, start_timestamp, end_timestamp, config):
    collector_class = tentacles_management.get_single_deepest_child_class(collector_parent_class)
    collector_instance = collector_class(config or {}, exchange_name, exchange_type,
                                         tentacles_setup_config, symbols, time_frames,
                                         use_all_available_timeframes=time_frames is None,
                                         start_timestamp=start_timestamp, end_timestamp=end_timestamp)
    return collector_instance


async def initialize_and_run_data_collector(data_collector):
    await data_collector.initialize()
    await data_collector.start()
    return data_collector.file_name


async def stop_data_collector(data_collector):
    return await data_collector.stop(should_stop_database=False) if data_collector else False


def is_data_collector_in_progress(data_collector):
    return data_collector.is_in_progress() if data_collector else False


def get_data_collector_progress(data_collector):
    return (data_collector.get_current_step_index(), data_collector.get_total_steps(),
            data_collector.get_current_step_percent()) if data_collector else (0, 0, 0)


def is_data_collector_finished(data_collector):
    return not is_data_collector_in_progress(
        data_collector) and data_collector.is_finished() if data_collector else False
