#  Drakkar-Software OctoBot
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
import os
import time
import asyncio

import octobot_backtesting.collectors as collector
import octobot_backtesting.enums as backtesting_enums
import octobot_backtesting.errors as errors
import octobot_commons.constants as commons_constants
import tentacles.Backtesting.importers.social.generic_social_importer as generic_social_importer

try:
    import octobot_services.api as services_api
    import octobot_services.errors as services_errors
except ImportError:
    logging.error("SocialHistoryDataCollector requires OctoBot-Services package installed")


class SocialHistoryDataCollector(collector.AbstractSocialHistoryCollector):
    IMPORTER = generic_social_importer.GenericSocialDataImporter

    def __init__(self, config, social_name, tentacles_setup_config, sources=None, symbols=None,
                 use_all_available_sources=False,
                 data_format=backtesting_enums.DataFormats.REGULAR_COLLECTOR_DATA,
                 start_timestamp=None,
                 end_timestamp=None):
        super().__init__(config, social_name, tentacles_setup_config=tentacles_setup_config,
                         sources=sources, symbols=symbols,
                         use_all_available_sources=use_all_available_sources,
                         data_format=data_format,
                         start_timestamp=start_timestamp, end_timestamp=end_timestamp)
        self.tentacles_setup_config = tentacles_setup_config
        self.feed_instance = None

    async def start(self):
        self.should_stop = False
        should_stop_database = True
        try:
            # Resolve feed class by name (social_name is feed name)
            feed_class = self._get_feed_class_by_name(self.social_name)
            if feed_class is None:
                available = [f.get_name() for f in services_api.get_available_backtestable_feeds()]
                raise errors.DataCollectorError(
                    f"Feed '{self.social_name}' not found. Available feeds: {available}"
                )

            # Create feed instance and ensure required services exist for it
            main_loop = asyncio.get_running_loop()
            bot_id = "social_collector"
            feed_factory = services_api.create_service_feed_factory(self.config, main_loop, bot_id)
            self.feed_instance = feed_factory.create_service_feed(feed_class)
            if feed_class.REQUIRED_SERVICES:
                service_instances = []
                for service_class in feed_class.REQUIRED_SERVICES:
                    svc = await services_api.get_service(
                        service_class, is_backtesting=True, config=self.config
                    )
                    service_instances.append(svc)
                self.feed_instance.services = service_instances

            self._load_sources_if_necessary()

            await self.check_timestamps()

            # create description
            await self._create_description()

            self.total_steps = len(self.sources) * (len(self.symbols) if self.symbols else 1)
            if self.total_steps == 0:
                self.total_steps = 1
            self.in_progress = True

            self.logger.info(f"Start collecting history on {self.social_name}")
            for source_index, source in enumerate(self.sources or [None]):
                if self.symbols:
                    for symbol_index, symbol in enumerate(self.symbols):
                        self.current_step_index = (source_index * len(self.symbols)) + symbol_index + 1
                        self.logger.info(f"Collecting history for {self.social_name} source={source} symbol={symbol}...")
                        await self.get_social_history(self.social_name, source, symbol)
                else:
                    self.current_step_index = source_index + 1
                    self.logger.info(f"Collecting history for {self.social_name} source={source}...")
                    await self.get_social_history(self.social_name, source, None)
        except Exception as err:
            await self.database.stop()
            should_stop_database = False
            # Do not keep errored data file
            if os.path.isfile(self.temp_file_path):
                os.remove(self.temp_file_path)
            if not self.should_stop:
                self.logger.exception(err, True, f"Error when collecting {self.social_name} history: {err}")
                raise errors.DataCollectorError(err)
        finally:
            await self.stop(should_stop_database=should_stop_database)

    def _get_feed_class_by_name(self, feed_name):
        """Find backtestable feed class by name."""
        feeds = services_api.get_available_backtestable_feeds()
        for feed_class in feeds:
            if feed_class.get_name() == feed_name or feed_class.get_name().lower() == feed_name.lower():
                return feed_class
        return None

    def _load_all_available_sources(self):
        # Override this if feed provides available sources
        pass

    async def stop(self, should_stop_database=True):
        self.should_stop = True
        if self.feed_instance is not None:
            await self.feed_instance.stop()
        if should_stop_database:
            await self.database.stop()
            self.finalize_database()
        self.feed_instance = None
        self.in_progress = False
        self.finished = True
        return self.finished

    async def get_social_history(self, feed_name, source, symbol=None):
        self.current_step_percent = 0

        # Use provided timestamps (required)
        start_time = self.start_timestamp
        end_time = self.end_timestamp or time.time() * 1000

        try:
            historical_data = self.feed_instance.get_historical_data(
                start_time, end_time, symbols=[symbol] if symbol else None, source=source
            )

            all_events = []
            async for batch in historical_data:
                if batch:  # batch is a list of events
                    all_events.extend(batch)
                    # Update progress
                    if all_events:
                        last_timestamp = all_events[-1].get('timestamp', time.time() * 1000)
                        self.current_step_percent = \
                            (last_timestamp - start_time) / ((end_time - start_time)) * 100
                        self.logger.info(
                            f"[{self.current_step_percent:.1f}%] historical data fetched for {feed_name} "
                            f"source={source} symbol={symbol}"
                        )

            if all_events:
                self.current_step_percent = 100
                self.logger.info(
                    f"[100%] historical data fetch complete for {feed_name} source={source} symbol={symbol}, saving..."
                )
                timestamps = [event.get('timestamp', time.time() * 1000) for event in all_events]
                channels = [event.get('channel', source or '') for event in all_events]
                symbols_list = [event.get('symbol', symbol or '') for event in all_events]
                payloads = [event.get('payload', event) for event in all_events]

                await self.save_event(
                    timestamp=timestamps,
                    service_name=feed_name,
                    channel=channels,
                    symbol=symbols_list,
                    payload=payloads,
                    multiple=True
                )
        except NotImplementedError:
            self.logger.warning(
                f"Feed {feed_name} does not implement get_historical_data. Skipping history collection."
            )
        except Exception as err:
            self.logger.exception(err, False)
            self.logger.warning(f"Ignored {feed_name} history collection ({err})")

    async def check_timestamps(self):
        if self.start_timestamp is None:
            raise errors.DataCollectorError("start_timestamp is required for social history collection")
        if self.start_timestamp > (self.end_timestamp if self.end_timestamp else (time.time() * 1000)):
            raise errors.DataCollectorError("start_timestamp is higher than end_timestamp")
