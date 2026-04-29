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

import tentacles.Services.Services_feeds.lunarcrush_service_feed.lunarcrush_feed as lunarcrush_feed


class LunarCrushServiceFeedSimulator(lunarcrush_feed.LunarCrushServiceFeed):
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
            for coin in self.lunarcrush_coins:
                channel = f"{coin};{services_constants.LUNARCRUSH_COIN_METRICS}"
                events = await self.social_data_importer.get_social_events_from_timestamps(
                    service_name=self.get_name(),
                    channel=channel,
                    symbol=coin,
                    inferior_timestamp=self.last_timestamp_pushed,
                    superior_timestamp=timestamp_ms
                )
                if events:
                    self.last_timestamp_pushed = timestamp_ms
                    # Update data_cache with events
                    self._update_cache_from_events(coin, events)
                    await self._async_notify_consumers(
                        {
                            services_constants.FEED_METADATA: channel,
                        }
                    )
        except errors.DatabaseNotFoundError as e:
            self.logger.warning(f"Not enough data: {e}")
            await self.pause()
            await self.stop()
        except IndexError as e:
            self.logger.warning(f"Failed to access social event data: {e}")

    def _update_cache_from_events(self, coin, events):
        """Update data_cache from social events for the given coin."""
        if services_constants.LUNARCRUSH_COIN_METRICS not in self.data_cache:
            self.data_cache[services_constants.LUNARCRUSH_COIN_METRICS] = {}
        
        self.data_cache[services_constants.LUNARCRUSH_COIN_METRICS][coin] = [
            lunarcrush_feed.LunarCrushCoinMetrics.from_dict(event["payload"])
            for event in events
        ]

    async def _start_service_feed(self):
        # In simulator mode, we don't start a live update loop
        # The time consumer callback handles data retrieval
        return True


lunarcrush_feed.LunarCrushServiceFeed.SIMULATOR_CLASS = LunarCrushServiceFeedSimulator
