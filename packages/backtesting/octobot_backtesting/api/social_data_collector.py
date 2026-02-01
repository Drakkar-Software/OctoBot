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


def social_historical_data_collector_factory(social_name,
                                            tentacles_setup_config,
                                            sources=None,
                                            symbols=None,
                                            start_timestamp=None,
                                            end_timestamp=None,
                                            config=None):
    """
    Factory function to create a social history data collector.
    :param social_name: Name of the service (e.g., "TwitterService", "TelegramService")
    :param tentacles_setup_config: Tentacles setup configuration
    :param sources: Optional list of sources/channels to collect from
    :param symbols: Optional list of symbols to filter by
    :param start_timestamp: Optional start timestamp in milliseconds
    :param end_timestamp: Optional end timestamp in milliseconds
    :param config: Optional configuration dict
    :return: SocialHistoryDataCollector instance
    """
    return _social_collector_factory(collectors.AbstractSocialHistoryCollector,
                                    social_name,
                                    tentacles_setup_config,
                                    sources,
                                    symbols,
                                    start_timestamp,
                                    end_timestamp,
                                    config)


def social_live_data_collector_factory(social_name,
                                       tentacles_setup_config,
                                       sources=None,
                                       symbols=None,
                                       service_feed_class=None,
                                       channel_name=None,
                                       config=None):
    """
    Factory function to create a social live data collector.
    :param social_name: Name of the service (e.g., "TwitterService", "TelegramService")
    :param tentacles_setup_config: Tentacles setup configuration
    :param sources: Optional list of sources/channels to collect from
    :param symbols: Optional list of symbols to filter by
    :param service_feed_class: Optional service feed class to subscribe to
    :param channel_name: Optional channel name to subscribe to directly
    :param config: Optional configuration dict
    :return: SocialLiveDataCollector instance
    """
    collector_class = tentacles_management.get_single_deepest_child_class(
        collectors.AbstractSocialLiveCollector
    )
    collector_instance = collector_class(
        config or {},
        social_name,
        tentacles_setup_config,
        sources=sources,
        symbols=symbols,
        service_feed_class=service_feed_class,
        channel_name=channel_name
    )
    return collector_instance


def _social_collector_factory(collector_parent_class, social_name, tentacles_setup_config,
                              sources, symbols, start_timestamp, end_timestamp, config):
    collector_class = tentacles_management.get_single_deepest_child_class(collector_parent_class)
    collector_instance = collector_class(
        config or {},
        social_name,
        tentacles_setup_config,
        sources=sources,
        symbols=symbols,
        use_all_available_sources=sources is None,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp
    )
    return collector_instance


from octobot_backtesting.api.exchange_data_collector import (
    initialize_and_run_data_collector,
    stop_data_collector,
    is_data_collector_in_progress,
    get_data_collector_progress,
    is_data_collector_finished,
)
