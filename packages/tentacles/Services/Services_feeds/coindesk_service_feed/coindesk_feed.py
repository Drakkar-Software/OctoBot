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

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_services.channel as services_channel
import octobot_services.constants as services_constants
import octobot_services.service_feeds as service_feeds
import tentacles.Services.Services_bases as Services_bases
import tentacles.Services.Services_bases.coindesk_service.models as coindesk_models


class CoindeskServiceFeedChannel(services_channel.AbstractServiceFeedChannel):
    pass


class CoindeskServiceFeed(service_feeds.AbstractServiceFeed):
    FEED_CHANNEL = CoindeskServiceFeedChannel
    REQUIRED_SERVICES = [Services_bases.CoindeskService]

    API_RATE_LIMIT_SECONDS = 10
    DEFAULT_HISTORICAL_LIMIT = 1000

    def __init__(self, config, main_async_loop, bot_id, backtesting=None, importer=None):
        super().__init__(config, main_async_loop, bot_id, backtesting=backtesting, importer=importer)
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

    @staticmethod
    def get_name() -> str:
        return "CoindeskServiceFeed"

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

    async def _get_marketcap_data(
        self,
        session: aiohttp.ClientSession,
        start_timestamp: typing.Optional[float] = None,
        end_timestamp: typing.Optional[float] = None,
    ) -> bool:
        async with session.get(self._get_marketcap_api_url()) as response:
            if response.status != 200:
                self.logger.error(f"Coindesk API request failed with status: {response.status}")
                return False

            market_cap_data = await response.json()

            new_values = [
                coindesk_models.CoindeskMarketcap(
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
            if start_timestamp is not None and end_timestamp is not None:
                def _marketcap_ts_ms(item):
                    t = item.timestamp
                    return int(t.timestamp() * 1000) if hasattr(t, "timestamp") else int(t)
                self.data_cache[services_constants.COINDESK_TOPIC_MARKETCAP] = [
                    item for item in self.data_cache[services_constants.COINDESK_TOPIC_MARKETCAP]
                    if start_timestamp <= _marketcap_ts_ms(item) <= end_timestamp
                ]
            return True


    def _get_news_api_url(self, limit: typing.Optional[int] = 10):
        return f"https://data-api.coindesk.com/news/v1/article/list?lang={self.coindesk_language}&limit={limit}"

    async def _get_news_data(
        self,
        session: aiohttp.ClientSession,
        limit: typing.Optional[int] = 10,
        start_timestamp: typing.Optional[float] = None,
        end_timestamp: typing.Optional[float] = None,
    ) -> bool:
        async with session.get(self._get_news_api_url(limit)) as response:
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

                values.append(coindesk_models.CoindeskNews(
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
            if start_timestamp is not None and end_timestamp is not None:
                def _news_ts_ms(item):
                    t = item.published_on
                    return int(t.timestamp() * 1000) if hasattr(t, "timestamp") else int(t)
                self.data_cache[services_constants.COINDESK_TOPIC_NEWS] = [
                    item for item in self.data_cache[services_constants.COINDESK_TOPIC_NEWS]
                    if start_timestamp <= _news_ts_ms(item) <= end_timestamp
                ]
            return True

    def get_data_cache(self, current_time: float, key: typing.Optional[str] = None):
        if self.data_cache is None:
            return None

        # Normalize current_time to seconds for comparisons
        if current_time is not None and current_time > 1e12:
            current_time = current_time / 1000

        if key is None:
            return self.data_cache

        def _to_seconds(value):
            if hasattr(value, "timestamp"):
                return float(value.timestamp())
            return value / 1000 if value > 1e12 else value

        if key == services_constants.COINDESK_TOPIC_NEWS and self.data_cache.get(services_constants.COINDESK_TOPIC_NEWS) is not None:
            return [
                item for item in self.data_cache.get(services_constants.COINDESK_TOPIC_NEWS)
                if _to_seconds(item.published_on) <= current_time
            ]
        elif key == services_constants.COINDESK_TOPIC_MARKETCAP and self.data_cache.get(services_constants.COINDESK_TOPIC_MARKETCAP) is not None:
            return [
                item for item in self.data_cache.get(services_constants.COINDESK_TOPIC_MARKETCAP)
                if _to_seconds(item.timestamp) <= current_time
            ]
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

    async def get_historical_data(
        self,
        start_timestamp,
        end_timestamp,
        symbols=None,
        source=None,
        **kwargs
    ) -> typing.AsyncIterator[list[dict]]:
        if start_timestamp is not None and start_timestamp < 1e12:
            start_timestamp = int(start_timestamp * 1000)
        if end_timestamp is not None and end_timestamp < 1e12:
            end_timestamp = int(end_timestamp * 1000)
        if not self.services and self.REQUIRED_SERVICES:
            self.services = [s.instance() for s in self.REQUIRED_SERVICES]
        if not self.services:
            return
        service = self.services[0]
        if source == services_constants.COINDESK_TOPIC_NEWS:
            async with aiohttp.ClientSession() as session:
                ok = await self._get_news_data(
                    session,
                    limit=self.DEFAULT_HISTORICAL_LIMIT,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                )
                await asyncio.sleep(self.API_RATE_LIMIT_SECONDS)
            if not ok or not self.data_cache.get(services_constants.COINDESK_TOPIC_NEWS):
                return
            events = [
                service._convert_news_to_event(item, source or services_constants.COINDESK_TOPIC_NEWS)
                for item in self.data_cache[services_constants.COINDESK_TOPIC_NEWS]
            ]
            events = [e for e in events if e is not None]
            if events:
                events.sort(key=lambda x: x["timestamp"])
                yield events
        elif source == services_constants.COINDESK_TOPIC_MARKETCAP:
            async with aiohttp.ClientSession() as session:
                ok = await self._get_marketcap_data(
                    session,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                )
                await asyncio.sleep(self.API_RATE_LIMIT_SECONDS)
            if not ok or not self.data_cache.get(services_constants.COINDESK_TOPIC_MARKETCAP):
                return
            events = [
                service._convert_marketcap_to_event(
                    item, source or services_constants.COINDESK_TOPIC_MARKETCAP
                )
                for item in self.data_cache[services_constants.COINDESK_TOPIC_MARKETCAP]
            ]
            events = [e for e in events if e is not None]
            if events:
                events.sort(key=lambda x: x["timestamp"])
                yield events
        else:
            raise ValueError(f"Invalid source: {source}")

    @classmethod
    def get_historical_sources(cls) -> list:
        return [services_constants.COINDESK_TOPIC_NEWS, services_constants.COINDESK_TOPIC_MARKETCAP]

    async def stop(self):
        await super().stop()
        if self.listener_task is not None:
            self.listener_task.cancel()
            self.listener_task = None
