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
import asyncio
import aiohttp
import typing
import dataclasses
import datetime

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_services.channel as services_channel
import octobot_services.constants as services_constants
import octobot_services.service_feeds as service_feeds
import tentacles.Services.Services_bases as Services_bases


class AlternativeMeServiceFeedChannel(services_channel.AbstractServiceFeedChannel):
    pass


@dataclasses.dataclass
class AlternativeMeFearAndGreed:
    timestamp: float
    value: float
    value_classification: str

class AlternativeMeServiceFeed(service_feeds.AbstractServiceFeed):
    FEED_CHANNEL = AlternativeMeServiceFeedChannel
    REQUIRED_SERVICES = [Services_bases.AlternativeMeService]

    API_RATE_LIMIT_SECONDS = 10

    def __init__(self, config, main_async_loop, bot_id):
        super().__init__(config, main_async_loop, bot_id)
        self.alternative_me_topics = []
        self.data_cache = {}
        self.refresh_time_frame = commons_enums.TimeFrames.ONE_DAY
        self.listener_task = None

    # merge new config into existing config
    def update_feed_config(self, config):
        self.alternative_me_topics.extend(topic
                                  for topic in config.get(services_constants.CONFIG_ALTERNATIVE_ME_TOPICS, [])
                                if topic not in self.alternative_me_topics)
        self.refresh_time_frame = config.get(services_constants.CONFIG_ALTERNATIVE_ME_REFRESH_TIME_FRAME, commons_enums.TimeFrames.ONE_DAY)

    def _initialize(self):
        pass # Nothing to do

    def _something_to_watch(self):
        return bool(self.alternative_me_topics)

    def _get_sleep_time_before_next_wakeup(self):
        return commons_enums.TimeFramesMinutes[self.refresh_time_frame] * commons_constants.MINUTE_TO_SECONDS

    async def _get_fear_and_greed_data(self, session: aiohttp.ClientSession, limit: typing.Optional[int] = 100) -> bool:
        api_url = f"https://api.alternative.me/fng/?limit={limit}&format=json&date_format=us"
        async with session.get(api_url) as response:
            if response.status != 200:
                self.logger.error(f"Alternative.me API request failed with status: {response.status}")
                return False

            fear_and_greed_data = await response.json()
            data = fear_and_greed_data["data"]
            self.data_cache[services_constants.ALTERNATIVE_ME_TOPIC_FEAR_AND_GREED] = [
                AlternativeMeFearAndGreed(
                    timestamp=datetime.datetime.strptime(entry["timestamp"], '%m-%d-%Y').replace(tzinfo=datetime.timezone.utc).timestamp(),
                    value=float(entry["value"]),
                    value_classification=entry["value_classification"]
                ) for entry in data]
            return True

    def get_data_cache(self, current_time: float, key: typing.Optional[str] = None):
        if self.data_cache is None:
            return None

        if key is None:
            return self.data_cache

        if key == services_constants.ALTERNATIVE_ME_TOPIC_FEAR_AND_GREED and self.data_cache.get(services_constants.ALTERNATIVE_ME_TOPIC_FEAR_AND_GREED) is not None:
            return [item for item in self.data_cache.get(services_constants.ALTERNATIVE_ME_TOPIC_FEAR_AND_GREED) if item.timestamp <= current_time]
        return None

    async def _push_update_and_wait(self, session: aiohttp.ClientSession):
        for topic in self.alternative_me_topics:
            self.logger.debug(f"Fetching alternative.me {topic} topic data...")
            result = False
            if topic == services_constants.ALTERNATIVE_ME_TOPIC_FEAR_AND_GREED:
                result = await self._get_fear_and_greed_data(session)

            if result:
                await self._async_notify_consumers(
                    {
                        services_constants.FEED_METADATA: topic,
                    }
                )
            await asyncio.sleep(self.API_RATE_LIMIT_SECONDS)
        await asyncio.sleep(self._get_sleep_time_before_next_wakeup())

    async def _update_loop(self):
        async with aiohttp.ClientSession() as session:
            while not self.should_stop:
                try:
                    await self._push_update_and_wait(session)
                except Exception as e:
                    self.logger.exception(e, True, f"Error when receiving Alternative.me data: ({e})")
                    await asyncio.sleep(self._get_sleep_time_before_next_wakeup())
            return False

    async def _start_service_feed(self):
        try:
            self.listener_task = asyncio.create_task(self._update_loop())
            return True
        except Exception as e:
            self.logger.exception(e, True, f"Error when initializing Alternative.me feed: {e}")
            return False

    async def stop(self):
        await super().stop()
        if self.listener_task is not None:
            self.listener_task.cancel()
            self.listener_task = None

