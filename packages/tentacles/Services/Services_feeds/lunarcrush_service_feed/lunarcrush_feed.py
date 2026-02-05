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
import datetime
import aiohttp
import json
import dataclasses
import typing

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.dataclasses as commons_dataclasses
import octobot_services.channel as services_channel
import octobot_services.constants as services_constants
import octobot_services.service_feeds as service_feeds
import tentacles.Services.Services_bases as Services_bases


class LunarCrushServiceFeedChannel(services_channel.AbstractServiceFeedChannel):
    pass


@dataclasses.dataclass
class LunarCrushCoinMetrics(commons_dataclasses.FlexibleDataclass):
    time: int # A unix timestamp (in seconds)
    contributors_active: int # number of unique social accounts with posts that have interactions
    contributors_created: int # number of unique social accounts that created new posts
    interactions: int # number of all publicly measurable interactions on a social post (views, likes, comments, thumbs up, upvote, share etc)
    posts_active: int # number of unique social posts with interactions
    posts_created: int # number of unique social posts created
    sentiment: float # % of posts (weighted by interactions) that are positive. 100% means all posts are positive, 50% is half positive and half negative, and 0% is all negative posts.
    spam: int # The number of posts created that are considered spam
    alt_rank: float # A proprietary score based on how an asset is performing relative to all other assets supported
    circulating_supply: int # Circulating Supply is the total number of coins or tokens that are actively available for trade and are being used in the market and in general public
    close: float # Close price for the time period
    galaxy_score: float # A proprietary score based on technical indicators of price, average social sentiment, relative social activity, and a factor of how closely social indicators correlate with price and volume
    high: float # Higest price fo rthe time period
    low: float # Lowest price for the time period
    market_cap: int # Total dollar market value of all circulating supply or outstanding shares
    market_dominance: float # The percent of the total market cap that this asset represents
    open: float # Open price for the time period
    social_dominance: float # The percent of the total social volume that this topic represents
    volume_24h: float # Volume in USD for 24 hours up to this data point

class LunarCrushServiceFeed(service_feeds.AbstractServiceFeed):
    FEED_CHANNEL = LunarCrushServiceFeedChannel
    REQUIRED_SERVICES = [Services_bases.LunarCrushService]

    def __init__(self, config, main_async_loop, bot_id, backtesting=None, importer=None):
        super().__init__(config, main_async_loop, bot_id, backtesting=backtesting, importer=importer)
        self.lunarcrush_coins = []
        self.data_cache = {}
        self.refresh_time_frame = commons_enums.TimeFrames.ONE_DAY
        self.listener_task = None

    # merge new config into existing config
    def update_feed_config(self, config):
        self.lunarcrush_coins.extend(coin
                                  for coin in config.get(services_constants.CONFIG_LUNARCRUSH_COINS, [])
                                  if coin not in self.lunarcrush_coins)
        self.refresh_time_frame = config.get(services_constants.CONFIG_LUNARCRUSH_REFRESH_TIME_FRAME, commons_enums.TimeFrames.ONE_DAY)

    def _initialize(self):
        pass # Nothing to do

    @staticmethod
    def get_name() -> str:
        return "LunarCrushServiceFeed"

    def _something_to_watch(self):
        return bool(self.lunarcrush_coins)

    def _get_sleep_time_before_next_wakeup(self):
        return commons_enums.TimeFramesMinutes[self.refresh_time_frame] * commons_constants.MINUTE_TO_SECONDS

    @classmethod
    def get_historical_sources(cls) -> list:
        return [
            services_constants.LUNARCRUSH_COIN_METRICS,
        ]

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
        coins = symbols or self.lunarcrush_coins
        if not coins:
            return
        start_date = datetime.datetime.fromtimestamp(start_timestamp / 1000, tz=datetime.timezone.utc)
        end_date = datetime.datetime.fromtimestamp(end_timestamp / 1000, tz=datetime.timezone.utc)
        headers = {}
        if self.services:
            headers = self.services[0].get_authentication_headers()
        async with aiohttp.ClientSession(headers=headers) as session:
            for coin in coins:
                events = []
                result = await self._get_coin_data(session, coin, start_date, end_date)
                data_by_coin = self.data_cache.get(services_constants.LUNARCRUSH_COIN_METRICS, {}) if result else {}
                coin_data = data_by_coin.get(coin, [])
                for item in coin_data:
                    ts_ms = int(item.time * 1000) if item.time < 1e12 else int(item.time)
                    if start_timestamp <= ts_ms <= end_timestamp:
                        payload = item.to_dict() if hasattr(item, "to_dict") else dataclasses.asdict(item)
                        events.append({
                            "timestamp": ts_ms,
                            "channel": f"{coin};{services_constants.LUNARCRUSH_COIN_METRICS}",
                            "symbol": coin,
                            "payload": payload,
                        })
                if events:
                    events.sort(key=lambda x: x["timestamp"])
                    yield events
                await asyncio.sleep(self.API_RATE_LIMIT_SECONDS)

    def get_data_cache(self, current_time: float, key: typing.Optional[str] = None):
        if self.data_cache is None:
            return None

        # Normalize current_time to seconds for comparisons
        if current_time is not None and current_time > 1e12:
            current_time = current_time / 1000

        if key is None:
            return self.data_cache

        coin, topic = key.split(";")
        if topic == services_constants.LUNARCRUSH_COIN_METRICS and self.data_cache.get(services_constants.LUNARCRUSH_COIN_METRICS) is not None:
            def _to_seconds(value):
                return value / 1000 if value > 1e12 else value
            return [
                item for item in self.data_cache.get(services_constants.LUNARCRUSH_COIN_METRICS).get(coin)
                if _to_seconds(item.time) <= current_time
            ]
        return None

    async def _get_coin_data(self, session: aiohttp.ClientSession, coin: str, start_date: datetime.datetime, end_date: datetime.datetime) -> bool:
        self.logger.debug(f"Getting lunarcrush coin data for {coin} from {start_date.timestamp()} to {end_date.timestamp()}...")
        api_url = f"https://lunarcrush.com/api3/public/coins/{coin}/time-series/v2?bucket=day&interval=1d&start={int(start_date.timestamp())}&end={int(end_date.timestamp())}"
        async with session.get(api_url) as response:
            if response.status != 200:
                self.logger.error(f"Lunarcrush API request failed with status: {response.status}")
                return False

            coin_metrics_data = await response.json()
            data = coin_metrics_data["data"]
            self.data_cache[services_constants.LUNARCRUSH_COIN_METRICS] = {
                coin: [
                    LunarCrushCoinMetrics.from_dict(entry)
                    for entry in data
                ]
            }
            return True

    async def _push_update_and_wait(self, session: aiohttp.ClientSession):
        end_date = datetime.datetime.now(datetime.timezone.utc)
        start_date = end_date - datetime.timedelta(days=30)
        for coin in self.lunarcrush_coins:
            result = await self._get_coin_data(session, coin, start_date, end_date)
            if result:
                await self._async_notify_consumers(
                    {
                        services_constants.FEED_METADATA: f"{coin};{services_constants.LUNARCRUSH_COIN_METRICS}",
                    }
                )
        await asyncio.sleep(self._get_sleep_time_before_next_wakeup())

    async def _update_loop(self):
        async with aiohttp.ClientSession(headers=self.services[0].get_authentication_headers()) as session:
            while not self.should_stop:
                try:
                    await self._push_update_and_wait(session)
                except Exception as e:
                    self.logger.exception(e, True, f"Error when receiving LunarCrush data: ({e})")
                    self.should_stop = True
            return False

    async def _start_service_feed(self):
        try:
            self.listener_task = asyncio.create_task(self._update_loop())
            return True
        except Exception as e:
            self.logger.exception(e, True, f"Error when initializing LunarCrush feed: {e}")
            return False

    async def stop(self):
        await super().stop()
        if self.listener_task is not None:
            self.listener_task.cancel()
            self.listener_task = None
