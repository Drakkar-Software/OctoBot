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
import datetime
import dataclasses

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_services.channel as services_channel
import octobot_services.constants as services_constants
import octobot_services.service_feeds as service_feeds
import tentacles.Services.Services_bases as Services_bases


class CoindeskServiceFeedChannel(services_channel.AbstractServiceFeedChannel):
    pass


@dataclasses.dataclass
class CoindeskNews:
    id: str
    guid: str
    published_on: datetime.datetime
    image_url: str
    title: str
    url: str
    source_id: str
    body: str
    keywords: str
    lang: str
    upvotes: int
    downvotes: int
    score: int
    sentiment: str # POSITIVE, NEGATIVE, NEUTRAL
    status: str
    source_name: str
    source_key: str
    source_url: str
    source_lang: str
    source_type: str
    categories: str

@dataclasses.dataclass
class CoindeskMarketcap:
    timestamp: datetime.datetime
    open: float
    close: float
    high: float
    low: float
    top_tier_volume: float

class CoindeskServiceFeed(service_feeds.AbstractServiceFeed):
    FEED_CHANNEL = CoindeskServiceFeedChannel
    REQUIRED_SERVICES = [Services_bases.CoindeskService]
    
    API_RATE_LIMIT_SECONDS = 10

    def __init__(self, config, main_async_loop, bot_id):
        super().__init__(config, main_async_loop, bot_id)
        self.coindesk_api_key = config.get(services_constants.CONFIG_COINDESK_API_KEY, None)
        self.coindesk_language = config.get(services_constants.CONFIG_COINDESK_LANGUAGE, "en")
        self.coindesk_topics = []
        self.data_cache = {}
        self.refresh_time_frame = commons_enums.TimeFrames.ONE_DAY
        self.listener_task = None

    # merge new config into existing config
    def update_feed_config(self, config):
        self.coindesk_topics.extend(topic
                                  for topic in config.get(services_constants.CONFIG_COINDESK_TOPICS, [])
                                  if topic not in self.coindesk_topics)
        self.refresh_time_frame = config.get(services_constants.CONFIG_COINDESK_REFRESH_TIME_FRAME, commons_enums.TimeFrames.ONE_DAY)
        self.coindesk_language = config.get(services_constants.CONFIG_COINDESK_LANGUAGE, "en")

    def _initialize(self):
        pass # Nothing to do

    def _something_to_watch(self):
        return bool(self.coindesk_topics)

    def _get_sleep_time_before_next_wakeup(self):
        return commons_enums.TimeFramesMinutes[self.refresh_time_frame] * commons_constants.MINUTE_TO_SECONDS

    def _merge_cache_data(self, cache_key: str, new_values: list, id_getter: typing.Callable) -> list:
        existing = self.data_cache.get(cache_key, [])
        existing_ids = {id_getter(item) for item in existing}
        new_unique = [item for item in new_values if id_getter(item) not in existing_ids]
        return existing + new_unique

    def _get_marketcap_api_url(self, limit: typing.Optional[int] = 2000):
        return f"https://data-api.coindesk.com/overview/v1/historical/marketcap/all/assets/days?limit={limit}&response_format=JSON"

    async def _get_marketcap_data(self, session: aiohttp.ClientSession) -> bool:
        async with session.get(self._get_marketcap_api_url()) as response:
            if response.status != 200:
                self.logger.error(f"Coindesk API request failed with status: {response.status}")
                return False

            market_cap_data = await response.json()

            new_values = [
                CoindeskMarketcap(
                    timestamp=entry["TIMESTAMP"],
                    open=entry["OPEN"],
                    close=entry["CLOSE"],
                    high=entry["HIGH"],
                    low=entry["LOW"],
                    top_tier_volume=entry["TOP_TIER_VOLUME"]
                ) for entry in market_cap_data["Data"]
            ]
            self.data_cache[services_constants.COINDESK_TOPIC_MARKETCAP] = self._merge_cache_data(
                services_constants.COINDESK_TOPIC_MARKETCAP, new_values, lambda x: x.timestamp
            )
            return True


    def _get_news_api_url(self, limit: typing.Optional[int] = 10):
        return f"https://data-api.coindesk.com/news/v1/article/list?lang={self.coindesk_language}&limit={limit}"

    async def _get_news_data(self, session: aiohttp.ClientSession) -> bool:
        async with session.get(self._get_news_api_url()) as response:
            if response.status != 200:
                self.logger.error(f"API request failed with status: {response.status}")
                return False

            news_data = await response.json()
            articles = news_data.get("Data", [])

            if not articles:
                self.logger.error("No articles found in API response")
                return False

            values = []
            for article in articles:
                source_data = article.get("SOURCE_DATA", {})
                category_data = article.get("CATEGORY_DATA", [])
                categories_str = str([cat["NAME"] for cat in category_data])

                values.append(CoindeskNews(
                    id=article["ID"],
                    guid=article["GUID"],
                    published_on=article["PUBLISHED_ON"],
                    image_url=article.get("IMAGE_URL", ""),
                    title=article["TITLE"],
                    url=article["URL"],
                    source_id=article["SOURCE_ID"],
                    body=article.get("BODY", ""),
                    keywords=article.get("KEYWORDS", ""),
                    lang=article["LANG"],
                    upvotes=article.get("UPVOTES", 0),
                    downvotes=article.get("DOWNVOTES", 0),
                    score=article.get("SCORE", 0),
                    sentiment=article.get("SENTIMENT", ""),
                    status=article.get("STATUS", "ACTIVE"),
                    source_name=source_data.get("NAME", ""),
                    source_key=source_data.get("SOURCE_KEY", ""),
                    source_url=source_data.get("URL", ""),
                    source_lang=source_data.get("LANG", ""),
                    source_type=source_data.get("SOURCE_TYPE", ""),
                    categories=categories_str
                ))

            self.data_cache[services_constants.COINDESK_TOPIC_NEWS] = self._merge_cache_data(
                services_constants.COINDESK_TOPIC_NEWS, values, lambda x: x.id
            )
            return True

    def get_data_cache(self, current_time: float, key: typing.Optional[str] = None):
        if self.data_cache is None:
            return None

        if key is None:
            return self.data_cache

        if key == services_constants.COINDESK_TOPIC_NEWS and self.data_cache.get(services_constants.COINDESK_TOPIC_NEWS) is not None:
            return [item for item in self.data_cache.get(services_constants.COINDESK_TOPIC_NEWS) if item.published_on <= current_time]
        elif key == services_constants.COINDESK_TOPIC_MARKETCAP and self.data_cache.get(services_constants.COINDESK_TOPIC_MARKETCAP) is not None:
            return [item for item in self.data_cache.get(services_constants.COINDESK_TOPIC_MARKETCAP) if item.timestamp <= current_time]
        return None
        
    async def _push_update_and_wait(self, session: aiohttp.ClientSession):
        for topic in self.coindesk_topics:
            self.logger.debug(f"Fetching coindesk {topic} topic data...")
            result = False
            if topic == services_constants.COINDESK_TOPIC_NEWS:
                result = await self._get_news_data(session)
            elif topic == services_constants.COINDESK_TOPIC_MARKETCAP:
                result = await self._get_marketcap_data(session)

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
                    self.logger.exception(e, True, f"Error when receiving Coindesk feed: ({e})")
                    await asyncio.sleep(self._get_sleep_time_before_next_wakeup())
            return False

    async def _start_service_feed(self):
        try:
            self.listener_task = asyncio.create_task(self._update_loop())
            return True
        except Exception as e:
            self.logger.exception(e, True, f"Error when initializing Coindesk feed: {e}")
            return False

    async def stop(self):
        await super().stop()
        if self.listener_task is not None:
            self.listener_task.cancel()
            self.listener_task = None
