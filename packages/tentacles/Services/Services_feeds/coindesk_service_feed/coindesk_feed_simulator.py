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
import octobot_commons.errors as errors

import octobot_services.constants as services_constants

import tentacles.Services.Services_feeds.coindesk_service_feed.coindesk_feed as coindesk_feed
import tentacles.Services.Services_bases.coindesk_service.models as coindesk_models


class CoindeskServiceFeedSimulator(coindesk_feed.CoindeskServiceFeed):
    IS_SIMULATOR_CLASS = True
    BACKTESTING_ENABLED = True
    
    def __init__(self, config, main_async_loop, bot_id, backtesting=None, importer=None):
        super().__init__(config, main_async_loop, bot_id, backtesting=backtesting, importer=importer)
        self.last_timestamp_pushed = 0

    def _something_to_watch(self):
        return self.social_data_importer is not None

    async def handle_timestamp(self, timestamp, **kwargs):
        try:
            timestamp_ms = int(timestamp * 1000) if timestamp < 1e12 else int(timestamp)
            if self.last_timestamp_pushed == 0:
                self.last_timestamp_pushed = timestamp_ms
            for topic in self.coindesk_topics:
                events = await self.social_data_importer.get_social_events_from_timestamps(
                    service_name=self.get_name(),
                    channel=topic,
                    inferior_timestamp=self.last_timestamp_pushed,
                    superior_timestamp=timestamp_ms
                )
                if events:
                    self.last_timestamp_pushed = timestamp_ms
                    self._update_cache_from_events(topic, events)
                    await self._async_notify_consumers(
                        {
                            services_constants.FEED_METADATA: topic,
                        }
                    )
        except errors.DatabaseNotFoundError as e:
            self.logger.warning(f"Not enough data: {e}")
            await self.pause()
            await self.stop()
        except IndexError as e:
            self.logger.warning(f"Failed to access social event data: {e}")

    def _update_cache_from_events(self, topic, events):
        """Update data_cache from social events for the given topic."""
        if topic == services_constants.COINDESK_TOPIC_NEWS:
            self.data_cache[topic] = [
                coindesk_models.CoindeskNews(
                    id=event["payload"].get("id", ""),
                    guid=event["payload"].get("guid", ""),
                    published_on=event["payload"].get("published_on", 0),
                    image_url=event["payload"].get("image_url", ""),
                    title=event["payload"].get("title", ""),
                    url=event["payload"].get("url", ""),
                    source_id=event["payload"].get("source_id", ""),
                    body=event["payload"].get("body", ""),
                    keywords=event["payload"].get("keywords", ""),
                    lang=event["payload"].get("lang", ""),
                    upvotes=event["payload"].get("upvotes", 0),
                    downvotes=event["payload"].get("downvotes", 0),
                    score=event["payload"].get("score", 0),
                    sentiment=event["payload"].get("sentiment", ""),
                    status=event["payload"].get("status", "ACTIVE"),
                    source_name=event["payload"].get("source_name", ""),
                    source_key=event["payload"].get("source_key", ""),
                    source_url=event["payload"].get("source_url", ""),
                    source_lang=event["payload"].get("source_lang", ""),
                    source_type=event["payload"].get("source_type", ""),
                    categories=event["payload"].get("categories", "")
                ) for event in events
            ]
        elif topic == services_constants.COINDESK_TOPIC_MARKETCAP:
            self.data_cache[topic] = [
                coindesk_models.CoindeskMarketcap(
                    timestamp=event["payload"].get("timestamp", 0),
                    open=event["payload"].get("open", 0),
                    close=event["payload"].get("close", 0),
                    high=event["payload"].get("high", 0),
                    low=event["payload"].get("low", 0),
                    top_tier_volume=event["payload"].get("top_tier_volume", 0)
                ) for event in events
            ]

    async def _start_service_feed(self):
        # In simulator mode, we don't start a live update loop
        # The time consumer callback handles data retrieval
        return True

coindesk_feed.CoindeskServiceFeed.SIMULATOR_CLASS = CoindeskServiceFeedSimulator
