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
import numpy

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.tentacles_management as tentacles_management
import octobot_evaluators.evaluators as evaluators
import octobot_services.constants as services_constants
import tentacles.Evaluator.Util as EvaluatorUtil
import tentacles.Services.Services_feeds as Services_feeds

class GoogleTrendsEvaluator(evaluators.SocialEvaluator):
    SERVICE_FEED_CLASS = Services_feeds.GoogleServiceFeed if hasattr(Services_feeds, 'GoogleServiceFeed') else None

    def __init__(self, tentacles_setup_config):
        evaluators.SocialEvaluator.__init__(self, tentacles_setup_config)
        self.stats_analyser = None
        self.refresh_rate_seconds = 86400
        self.relevant_history_months = 3

    def init_user_inputs(self, inputs: dict) -> None:
        self.refresh_rate_seconds = self.refresh_rate_seconds or \
            self.UI.user_input(commons_constants.CONFIG_REFRESH_RATE,
                               commons_enums.UserInputTypes.INT,
                               self.refresh_rate_seconds, inputs, min_val=1,
                               title="Seconds between each re-evaluation (do not set too low because google has a low "
                                     "monthly rate limit).")
        self.relevant_history_months = self.UI.user_input(services_constants.CONFIG_TREND_HISTORY_TIME,
                                                       commons_enums.UserInputTypes.INT,
                                                       self.relevant_history_months, inputs, min_val=3, max_val=3,
                                                       title="Number of months to look into to compute the trend "
                                                             "evaluation (for now works only with 3).")
        self.feed_config[services_constants.CONFIG_TREND_TOPICS] = self._build_trend_topics()

    @classmethod
    def get_is_cryptocurrencies_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency dependant else False
        """
        return False

    @classmethod
    def get_is_cryptocurrency_name_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency name dependant else False
        """
        return False

    async def _feed_callback(self, data):
        if self._is_interested_by_this_notification(data[services_constants.FEED_METADATA]):
            trend = numpy.array([d["data"] for d in data[services_constants.CONFIG_TREND]])
            # compute bollinger bands
            self.eval_note = self.stats_analyser.analyse_recent_trend_changes(trend, numpy.sqrt)
            await self.evaluation_completed(self.cryptocurrency, eval_time=self.get_current_exchange_time())

    def _is_interested_by_this_notification(self, notification_description):
        return self.cryptocurrency_name in notification_description

    def _build_trend_topics(self):
        trend_time_frame = f"today {self.relevant_history_months}-m"
        return [
            Services_feeds.TrendTopic(self.refresh_rate_seconds,
                                      [self.cryptocurrency_name],
                                      time_frame=trend_time_frame)
        ]

    async def prepare(self):
        self.stats_analyser = tentacles_management.get_single_deepest_child_class(EvaluatorUtil.StatisticAnalysis)()

CONFIG_TREND_AVERAGES = "trend_averages"

class MarketCapEvaluator(evaluators.SocialEvaluator):
    SERVICE_FEED_CLASS = Services_feeds.CoindeskServiceFeed

    def __init__(self, tentacles_setup_config):
        evaluators.SocialEvaluator.__init__(self, tentacles_setup_config)
        self.stats_analyser = None
        self.feed_config = {
            services_constants.CONFIG_COINDESK_TOPICS: [services_constants.COINDESK_TOPIC_MARKETCAP]
        }
        self.trend_averages = [40, 30, 20, 15, 10]

    def init_user_inputs(self, inputs: dict) -> None:
        self.trend_averages = self.UI.user_input(CONFIG_TREND_AVERAGES,
                                                 commons_enums.UserInputTypes.OBJECT_ARRAY,
                                                 self.trend_averages, inputs,
                                                 title="Averages to use to compute the trend evaluation.")

    @classmethod
    def get_is_cryptocurrencies_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency dependant else False
        """
        return True

    @classmethod
    def get_is_cryptocurrency_name_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency name dependant else False
        """
        return True

    async def _feed_callback(self, data):
        if self._is_interested_by_this_notification(data[services_constants.FEED_METADATA]):
            marketcap_data = self.get_data_cache(self.get_current_exchange_time(), key=services_constants.COINDESK_TOPIC_MARKETCAP)
            if marketcap_data is not None and len(marketcap_data) > 0:
                marketcap_history = [item.close for item in marketcap_data]
                self.eval_note = self.stats_analyser.get_trend(marketcap_history, self.trend_averages)
                await self.evaluation_completed(cryptocurrency=None, 
                                                eval_time=self.get_current_exchange_time(),
                                                eval_note_description="Latest market cap values: " + ", ".join([str(v) for v in marketcap_history[-5:]]))

    def _is_interested_by_this_notification(self, notification_description):
        return notification_description == services_constants.COINDESK_TOPIC_MARKETCAP

    async def prepare(self):
        self.stats_analyser = tentacles_management.get_single_deepest_child_class(EvaluatorUtil.TrendAnalysis)()


class CryptoMarketCapEvaluator(evaluators.SocialEvaluator):
    SERVICE_FEED_CLASS = Services_feeds.CoingeckoServiceFeed

    def __init__(self, tentacles_setup_config):
        evaluators.SocialEvaluator.__init__(self, tentacles_setup_config)
        self.feed_config = {
            services_constants.CONFIG_COINGECKO_TOPICS: [services_constants.COINGECKO_TOPIC_MARKETS]
        }

    @classmethod
    def get_is_cryptocurrencies_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency dependant else False
        """
        return False

    @classmethod
    def get_is_cryptocurrency_name_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency name dependant else False
        """
        return False

    async def _feed_callback(self, data):
        if self._is_interested_by_this_notification(data[services_constants.FEED_METADATA]):
            markets_data = self.get_data_cache(self.get_current_exchange_time(), key=services_constants.COINGECKO_TOPIC_MARKETS)
            if markets_data is not None and len(markets_data) > 0:
                # Find the coin in the markets data by symbol (case-insensitive)
                coin_data = None
                for market_coin in markets_data:
                    if market_coin.symbol and market_coin.symbol.upper() == self.cryptocurrency.upper():
                        coin_data = market_coin
                        break
                
                if coin_data is None:
                    # Coin not found in top 100, return neutral eval note
                    self.eval_note = 0.0
                    await self.evaluation_completed(
                        cryptocurrency=self.cryptocurrency,
                        eval_time=self.get_current_exchange_time(),
                        eval_note_description=f"{self.cryptocurrency} not found in top 100 market cap coins"
                    )
                    return
                
                # Calculate base signal from market_cap_change_percentage_24h
                market_cap_change = coin_data.market_cap_change_percentage_24h or 0.0
                market_cap_signal = max(-1.0, min(1.0, market_cap_change / 50.0))
                
                # Calculate price signal
                price_change = coin_data.price_change_percentage_24h or 0.0
                price_signal = max(-1.0, min(1.0, price_change / 20.0))
                
                # Calculate position weight (higher rank = more established = higher confidence)
                rank = coin_data.market_cap_rank or 100
                position_weight = max(0.7, 1.0 - (rank - 1) / 100.0)
                
                # Calculate volume factor (normalize by max volume in top 100)
                max_volume = max((coin.total_volume or 0.0) for coin in markets_data)
                volume_factor = 1.0
                if max_volume > 0:
                    volume_factor = min(1.0, (coin_data.total_volume or 0.0) / max_volume)
                
                # Combine all factors
                eval_note = (market_cap_signal * 0.6 + price_signal * 0.3 + volume_factor * 0.1) * position_weight
                eval_note = max(-1.0, min(1.0, eval_note))
                
                self.eval_note = eval_note
                await self.evaluation_completed(
                    cryptocurrency=self.cryptocurrency,
                    eval_time=self.get_current_exchange_time(),
                    eval_note_description=f"Rank: {rank}, Market Cap Change: {market_cap_change:.2f}%, Price Change: {price_change:.2f}%, Position Weight: {position_weight:.2f}"
                )

    def _is_interested_by_this_notification(self, notification_description):
        return notification_description == services_constants.COINGECKO_TOPIC_MARKETS
