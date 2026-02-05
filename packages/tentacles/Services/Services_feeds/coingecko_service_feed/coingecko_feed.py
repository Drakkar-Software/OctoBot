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
import typing
import dataclasses

import coingecko_openapi_client

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.dataclasses as commons_dataclasses
import octobot_services.channel as services_channel
import octobot_services.constants as services_constants
import octobot_services.service_feeds as service_feeds
import tentacles.Services.Services_bases as Services_bases


class CoingeckoServiceFeedChannel(services_channel.AbstractServiceFeedChannel):
    pass


@dataclasses.dataclass
class CoingeckoCoinMarket(commons_dataclasses.FlexibleDataclass):
    id: str
    symbol: str
    name: str
    current_price: float
    market_cap: float
    market_cap_rank: int
    total_volume: float
    high_24h: float
    low_24h: float
    price_change_24h: float
    price_change_percentage_24h: float
    market_cap_change_24h: float
    market_cap_change_percentage_24h: float
    circulating_supply: float
    total_supply: float
    ath: float
    ath_change_percentage: float
    atl: float
    atl_change_percentage: float
    last_updated: str


@dataclasses.dataclass
class CoingeckoTrendingCoin(commons_dataclasses.FlexibleDataclass):
    id: str
    coin_id: int
    name: str
    symbol: str
    market_cap_rank: int
    thumb: str
    small: str
    large: str
    slug: str
    price_btc: float
    score: int


@dataclasses.dataclass
class CoingeckoGlobalData(commons_dataclasses.FlexibleDataclass):
    active_cryptocurrencies: int
    upcoming_icos: int
    ongoing_icos: int
    ended_icos: int
    markets: int
    total_market_cap: dict
    total_volume: dict
    market_cap_percentage: dict
    market_cap_change_percentage_24h_usd: float
    updated_at: int


class CoingeckoServiceFeed(service_feeds.AbstractServiceFeed):
    FEED_CHANNEL = CoingeckoServiceFeedChannel
    REQUIRED_SERVICES = [Services_bases.CoingeckoService]

    API_RATE_LIMIT_SECONDS = 10

    def __init__(self, config, main_async_loop, bot_id, backtesting=None, importer=None):
        super().__init__(config, main_async_loop, bot_id, backtesting=backtesting, importer=importer)
        self.coingecko_topics = []
        self.coingecko_coins = []
        self.data_cache = {}
        self.refresh_time_frame = commons_enums.TimeFrames.ONE_DAY
        self.listener_task = None
        self.api_client = None
        self.coins_api = None
        self.trending_api = None
        self.global_api = None

    def _initialize_api_client(self):
        self.api_client = coingecko_openapi_client.ApiClient()
        self.coins_api = coingecko_openapi_client.api.coins_api.CoinsApi(self.api_client)
        self.trending_api = coingecko_openapi_client.api.trending_api.TrendingApi(self.api_client)
        self.global_api = coingecko_openapi_client.api.global_api.GlobalApi(self.api_client)

    # merge new config into existing config
    def update_feed_config(self, config):
        self.coingecko_topics.extend(
            topic
            for topic in config.get(services_constants.CONFIG_COINGECKO_TOPICS, [])
            if topic not in self.coingecko_topics
        )
        self.coingecko_coins.extend(
            coin
            for coin in config.get(services_constants.CONFIG_COINGECKO_COINS, [])
            if coin not in self.coingecko_coins
        )
        self.refresh_time_frame = config.get(
            services_constants.CONFIG_COINGECKO_REFRESH_TIME_FRAME,
            commons_enums.TimeFrames.ONE_DAY
        )

    def _initialize(self):
        self._initialize_api_client()

    @staticmethod
    def get_name() -> str:
        return "CoingeckoServiceFeed"

    def _something_to_watch(self):
        return bool(self.coingecko_topics)

    def _get_sleep_time_before_next_wakeup(self):
        return commons_enums.TimeFramesMinutes[self.refresh_time_frame] * commons_constants.MINUTE_TO_SECONDS

    @classmethod
    def get_historical_sources(cls) -> list:
        return [
            services_constants.COINGECKO_TOPIC_MARKETS,
            services_constants.COINGECKO_TOPIC_TRENDING,
            services_constants.COINGECKO_TOPIC_GLOBAL,
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
        if self.api_client is None:
            self._initialize_api_client()

        topics = [source] if source else (self.coingecko_topics or self.get_historical_sources())
        for topic in topics:
            events = []
            result = False
            if topic == services_constants.COINGECKO_TOPIC_MARKETS:
                result = await self._get_markets_data()
                data = self.data_cache.get(services_constants.COINGECKO_TOPIC_MARKETS, []) if result else []
                for item in data:
                    payload = item.to_dict() if hasattr(item, "to_dict") else dataclasses.asdict(item)
                    events.append({
                        "timestamp": end_timestamp,
                        "channel": topic,
                        "symbol": item.symbol if hasattr(item, "symbol") else "",
                        "payload": payload,
                    })
            elif topic == services_constants.COINGECKO_TOPIC_TRENDING:
                result = await self._get_trending_data()
                data = self.data_cache.get(services_constants.COINGECKO_TOPIC_TRENDING, []) if result else []
                for item in data:
                    payload = item.to_dict() if hasattr(item, "to_dict") else dataclasses.asdict(item)
                    events.append({
                        "timestamp": end_timestamp,
                        "channel": topic,
                        "symbol": item.symbol if hasattr(item, "symbol") else "",
                        "payload": payload,
                    })
            elif topic == services_constants.COINGECKO_TOPIC_GLOBAL:
                result = await self._get_global_data()
                data = self.data_cache.get(services_constants.COINGECKO_TOPIC_GLOBAL) if result else None
                if data is not None:
                    payload = data.to_dict() if hasattr(data, "to_dict") else dataclasses.asdict(data)
                    events.append({
                        "timestamp": end_timestamp,
                        "channel": topic,
                        "symbol": "",
                        "payload": payload,
                    })

            if events:
                yield events
            await asyncio.sleep(self.API_RATE_LIMIT_SECONDS)

    async def _get_markets_data(self, per_page: int = 100) -> bool:
        try:
            self.logger.debug("Fetching coingecko markets data...")
            markets_data = await self.coins_api.coins_markets_get(
                vs_currency='usd',
                per_page=per_page,
                order='market_cap_desc'
            )
            self.data_cache[services_constants.COINGECKO_TOPIC_MARKETS] = [
                CoingeckoCoinMarket.from_dict({
                    'id': coin.get('id', ''),
                    'symbol': coin.get('symbol', ''),
                    'name': coin.get('name', ''),
                    'current_price': coin.get('current_price', 0.0),
                    'market_cap': coin.get('market_cap', 0),
                    'market_cap_rank': coin.get('market_cap_rank', 0),
                    'total_volume': coin.get('total_volume', 0.0),
                    'high_24h': coin.get('high_24h', 0.0),
                    'low_24h': coin.get('low_24h', 0.0),
                    'price_change_24h': coin.get('price_change_24h', 0.0),
                    'price_change_percentage_24h': coin.get('price_change_percentage_24h', 0.0),
                    'market_cap_change_24h': coin.get('market_cap_change_24h', 0.0),
                    'market_cap_change_percentage_24h': coin.get('market_cap_change_percentage_24h', 0.0),
                    'circulating_supply': coin.get('circulating_supply', 0.0),
                    'total_supply': coin.get('total_supply', 0.0),
                    'ath': coin.get('ath', 0.0),
                    'ath_change_percentage': coin.get('ath_change_percentage', 0.0),
                    'atl': coin.get('atl', 0.0),
                    'atl_change_percentage': coin.get('atl_change_percentage', 0.0),
                    'last_updated': coin.get('last_updated', ''),
                })
                for coin in markets_data
            ]
            return True
        except Exception as e:
            self.logger.error(f"Coingecko markets API request failed: {e}")
            return False

    async def _get_trending_data(self) -> bool:
        try:
            self.logger.debug("Fetching coingecko trending data...")
            trending_data = await self.trending_api.search_trending_get()
            coins = trending_data.get('coins', [])
            self.data_cache[services_constants.COINGECKO_TOPIC_TRENDING] = [
                CoingeckoTrendingCoin.from_dict({
                    'id': coin.get('item', {}).get('id', ''),
                    'coin_id': coin.get('item', {}).get('coin_id', 0),
                    'name': coin.get('item', {}).get('name', ''),
                    'symbol': coin.get('item', {}).get('symbol', ''),
                    'market_cap_rank': coin.get('item', {}).get('market_cap_rank', 0),
                    'thumb': coin.get('item', {}).get('thumb', ''),
                    'small': coin.get('item', {}).get('small', ''),
                    'large': coin.get('item', {}).get('large', ''),
                    'slug': coin.get('item', {}).get('slug', ''),
                    'price_btc': coin.get('item', {}).get('price_btc', 0.0),
                    'score': coin.get('item', {}).get('score', 0),
                })
                for coin in coins
            ]
            return True
        except Exception as e:
            self.logger.error(f"Coingecko trending API request failed: {e}")
            return False

    async def _get_global_data(self) -> bool:
        try:
            self.logger.debug("Fetching coingecko global data...")
            global_data = await self.global_api.global_get()
            if not global_data:
                self.logger.error("Coingecko global API returned empty payload")
                return False
            data = global_data.get('data', {})
            self.data_cache[services_constants.COINGECKO_TOPIC_GLOBAL] = CoingeckoGlobalData.from_dict({
                'active_cryptocurrencies': data.get('active_cryptocurrencies', 0),
                'upcoming_icos': data.get('upcoming_icos', 0),
                'ongoing_icos': data.get('ongoing_icos', 0),
                'ended_icos': data.get('ended_icos', 0),
                'markets': data.get('markets', 0),
                'total_market_cap': data.get('total_market_cap', {}),
                'total_volume': data.get('total_volume', {}),
                'market_cap_percentage': data.get('market_cap_percentage', {}),
                'market_cap_change_percentage_24h_usd': data.get('market_cap_change_percentage_24h_usd', 0.0),
                'updated_at': data.get('updated_at', 0),
            })
            return True
        except Exception as e:
            self.logger.error(f"Coingecko global API request failed: {e}")
            return False

    def get_data_cache(self, current_time: float, key: typing.Optional[str] = None):
        if self.data_cache is None:
            return None

        if key is None:
            return self.data_cache

        if key == services_constants.COINGECKO_TOPIC_MARKETS:
            return self.data_cache.get(services_constants.COINGECKO_TOPIC_MARKETS)
        elif key == services_constants.COINGECKO_TOPIC_TRENDING:
            return self.data_cache.get(services_constants.COINGECKO_TOPIC_TRENDING)
        elif key == services_constants.COINGECKO_TOPIC_GLOBAL:
            return self.data_cache.get(services_constants.COINGECKO_TOPIC_GLOBAL)
        return None

    async def _push_update_and_wait(self):
        for topic in self.coingecko_topics:
            self.logger.debug(f"Fetching coingecko {topic} topic data...")
            result = False
            if topic == services_constants.COINGECKO_TOPIC_MARKETS:
                result = await self._get_markets_data()
            elif topic == services_constants.COINGECKO_TOPIC_TRENDING:
                result = await self._get_trending_data()
            elif topic == services_constants.COINGECKO_TOPIC_GLOBAL:
                result = await self._get_global_data()

            if result:
                await self._async_notify_consumers(
                    {
                        services_constants.FEED_METADATA: topic,
                    }
                )
            await asyncio.sleep(self.API_RATE_LIMIT_SECONDS)
        await asyncio.sleep(self._get_sleep_time_before_next_wakeup())

    async def _update_loop(self):
        while not self.should_stop:
            try:
                await self._push_update_and_wait()
            except Exception as e:
                self.logger.exception(e, True, f"Error when receiving Coingecko data: ({e})")
                await asyncio.sleep(self._get_sleep_time_before_next_wakeup())
        return False

    async def _start_service_feed(self):
        try:
            self.listener_task = asyncio.create_task(self._update_loop())
            return True
        except Exception as e:
            self.logger.exception(e, True, f"Error when initializing Coingecko feed: {e}")
            return False

    async def stop(self):
        await super().stop()
        if self.listener_task is not None:
            self.listener_task.cancel()
            self.listener_task = None
