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
import octobot_commons.enums as commons_enums
import octobot_commons.tentacles_management as tentacles_management
import octobot_evaluators.evaluators as evaluators
import octobot_services.constants as services_constants
import tentacles.Evaluator.Util as EvaluatorUtil
import tentacles.Services.Services_feeds as Services_feeds

CONFIG_TREND_AVERAGES = "trend_averages"

class FearAndGreedIndexEvaluator(evaluators.SocialEvaluator):
    SERVICE_FEED_CLASS = Services_feeds.AlternativeMeServiceFeed

    def __init__(self, tentacles_setup_config):
        evaluators.SocialEvaluator.__init__(self, tentacles_setup_config)
        self.stats_analyser = None
        self.history_data = None
        self.feed_config = {
            services_constants.CONFIG_ALTERNATIVE_ME_TOPICS: [services_constants.ALTERNATIVE_ME_TOPIC_FEAR_AND_GREED]
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
            fear_and_greed_history = self.get_data_cache(self.get_current_exchange_time(), key=services_constants.ALTERNATIVE_ME_TOPIC_FEAR_AND_GREED)
            if fear_and_greed_history is not None and len(fear_and_greed_history) > 0:
                fear_and_greed_history_values = [item.value for item in fear_and_greed_history]
                self.eval_note = self.stats_analyser.get_trend(fear_and_greed_history_values, self.trend_averages)
                await self.evaluation_completed(cryptocurrency=None, 
                                                eval_time=self.get_current_exchange_time(), 
                                                eval_note_description="Latest values: " + ", ".join([str(v) for v in fear_and_greed_history_values[-5:]]))

    def _is_interested_by_this_notification(self, notification_description):
        return notification_description == services_constants.ALTERNATIVE_ME_TOPIC_FEAR_AND_GREED

    async def prepare(self):
        self.stats_analyser = tentacles_management.get_single_deepest_child_class(EvaluatorUtil.TrendAnalysis)()

class SocialScoreEvaluator(evaluators.SocialEvaluator):
    SERVICE_FEED_CLASS = Services_feeds.LunarCrushServiceFeed

    def __init__(self, tentacles_setup_config):
        evaluators.SocialEvaluator.__init__(self, tentacles_setup_config)
        self.stats_analyser = None

    def init_user_inputs(self, inputs: dict) -> None:
        self.feed_config = {
            services_constants.CONFIG_LUNARCRUSH_COINS: [self.cryptocurrency]
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
            coin, _ = data[services_constants.FEED_METADATA].split(";")
            coin_data = self.get_data_cache(self.get_current_exchange_time(), key=f"{coin};{services_constants.LUNARCRUSH_COIN_METRICS}")
            if coin_data is not None and len(coin_data) > 0:
                self.eval_note = coin_data[-1].sentiment
                await self.evaluation_completed(cryptocurrency=self.cryptocurrency, eval_time=self.get_current_exchange_time())

    def _is_interested_by_this_notification(self, notification_description):
        try:
            coin, topic = notification_description.split(";")
            return coin == self.cryptocurrency and topic == services_constants.LUNARCRUSH_COIN_METRICS
        except KeyError:
            pass
        return False
