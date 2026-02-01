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
import asyncio
import logging
import time

import octobot_backtesting.collectors as collector
import octobot_backtesting.enums as backtesting_enums
import async_channel.channels as channels

try:
    import octobot_services.api as services_api
    import octobot_services.service_feeds as service_feeds
    import octobot_services.service_feeds.service_feed_factory as service_feed_factory
except ImportError:
    logging.error("SocialLiveDataCollector requires OctoBot-Services package installed")


class SocialLiveDataCollector(collector.AbstractSocialLiveCollector):
    IMPORTER = None  # Live collectors typically don't need importers

    def __init__(self, config, social_name, tentacles_setup_config, sources=None, symbols=None,
                 service_feed_class=None, channel_name=None,
                 data_format=backtesting_enums.DataFormats.REGULAR_COLLECTOR_DATA):
        super().__init__(config, social_name, sources=sources, symbols=symbols,
                         data_format=data_format)
        self.tentacles_setup_config = tentacles_setup_config
        self.service_feed_class = service_feed_class
        self.channel_name = channel_name
        self.bot_id = "live_collector"  # Default bot_id for live collector
        self.consumers = []

    async def start(self):
        await self.initialize()
        self._load_sources_if_necessary()

        # create description
        await self._create_description()

        # Find service feed channels to consume from
        feed_channels = await self._get_service_feed_channels()
        
        if not feed_channels:
            self.logger.warning(
                f"No service feed channels found for {self.social_name}. "
                f"Make sure service feeds are running."
            )
            return

        # Subscribe to all found channels
        for channel_name, channel in feed_channels.items():
            self.logger.info(f"Subscribing to service feed channel: {channel_name}")
            consumer = await channel.new_consumer(self._service_feed_callback)
            self.consumers.append(consumer)

        self.logger.info(f"Started collecting live data from {self.social_name}")
        # Keep running until stopped
        await asyncio.gather(*asyncio.all_tasks(asyncio.get_event_loop()))

    async def _get_service_feed_channels(self):
        """Get service feed channels associated with the social service"""
        feed_channels = {}
        
        # If channel_name is provided, use it directly
        if self.channel_name:
            try:
                channel = channels.get_chan(self.channel_name)
                feed_channels[self.channel_name] = channel
                return feed_channels
            except KeyError:
                self.logger.warning(f"Channel {self.channel_name} not found")
        
        # If service_feed_class is provided, use it
        if self.service_feed_class:
            try:
                service_feed = services_api.get_service_feed(self.service_feed_class, self.bot_id)
                if service_feed and service_feed.FEED_CHANNEL:
                    channel_name = service_feed.FEED_CHANNEL.get_name()
                    channel = channels.get_chan(channel_name)
                    feed_channels[channel_name] = channel
                    return feed_channels
            except (RuntimeError, KeyError) as err:
                self.logger.warning(f"Could not get service feed {self.service_feed_class}: {err}")
        
        # Try to find service feeds associated with the service name
        available_feeds = service_feed_factory.ServiceFeedFactory.get_available_service_feeds(in_backtesting=False)
        for feed_class in available_feeds:
            # Check if feed name matches social_name or is related
            feed_name = feed_class.get_name().lower()
            social_name_lower = self.social_name.lower()
            if social_name_lower in feed_name or feed_name in social_name_lower:
                try:
                    service_feed = services_api.get_service_feed(feed_class, self.bot_id)
                    if service_feed and service_feed.FEED_CHANNEL:
                        channel_name = service_feed.FEED_CHANNEL.get_name()
                        channel = channels.get_chan(channel_name)
                        feed_channels[channel_name] = channel
                        self.logger.info(f"Found matching service feed: {feed_class.get_name()}")
                except (RuntimeError, KeyError):
                    continue
        
        return feed_channels

    async def _service_feed_callback(self, data):
        """Callback for service feed channel messages"""
        try:
            # Extract data from the channel message
            # Service feed channels send: {"data": actual_data}
            event_data = data.get("data", data)
            
            # Extract metadata
            service_name = self.social_name
            channel = data.get("channel", "")
            symbol = event_data.get("symbol") if isinstance(event_data, dict) else None
            timestamp = event_data.get("timestamp", time.time() * 1000) if isinstance(event_data, dict) else time.time() * 1000
            
            # Prepare payload
            if isinstance(event_data, dict):
                payload = event_data
            else:
                payload = {"data": event_data}
            
            self.logger.info(
                f"LIVE EVENT : SERVICE = {service_name} || CHANNEL = {channel} || "
                f"SYMBOL = {symbol} || TIMESTAMP = {timestamp}"
            )
            
            await self.save_event(
                timestamp=timestamp,
                service_name=service_name,
                channel=channel,
                symbol=symbol,
                payload=payload
            )
        except Exception as err:
            self.logger.exception(err, False, f"Error processing service feed event: {err}")

    async def stop(self, should_stop_database=True):
        self.should_stop = True
        
        # Stop all consumers
        for consumer in self.consumers:
            await consumer.stop()
        self.consumers = []
        
        if should_stop_database:
            await self.database.stop()
            self.finalize_database()
        
        self.in_progress = False
        self.finished = True
        return self.finished
