#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import decimal
import time
import sortedcontainers

import async_channel
import async_channel.enums as channel_enums
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.configuration as configuration
import octobot_commons.channels_name as channels_name
import octobot_trading.constants as trading_constants
import octobot_trading.exchange_channel as exchanges_channel
import octobot.automation.bases.abstract_channel_based_trigger_event as abstract_channel_based_trigger_event


class ProfitabilityThreshold(abstract_channel_based_trigger_event.AbstractChannelBasedTriggerEvent):
    PERCENT_CHANGE = "percent_change"
    TIME_PERIOD = "time_period"
    TRIGGER_ONLY_ONCE = "trigger_only_once"
    MAX_TRIGGER_FREQUENCY = "max_trigger_frequency"

    def __init__(self):
        super().__init__()
        self.percent_change: decimal.Decimal = None # type: ignore
        self.time_period: int = None # type: ignore
        self.profitability_by_time: sortedcontainers.SortedDict = None # type: ignore

    async def register_consumers(self, exchange_id: str) -> list[async_channel.Consumer]:
        return [
            await exchanges_channel.get_chan(
                channels_name.OctoBotTradingChannelsName.BALANCE_PROFITABILITY_CHANNEL.value, exchange_id
            ).new_consumer(
                self.profitability_callback,
                priority_level=channel_enums.ChannelConsumerPriorityLevels.HIGH.value,
            )
        ]

    async def profitability_callback(
        self,
        exchange: str,
        exchange_id: str,
        profitability,
        profitability_percent,
        market_profitability_percent,
        initial_portfolio_current_profitability,
    ):
        if self.should_stop:
            # do not go any further if the action has been stopped
            return
        self._update_profitability_by_time(profitability_percent)
        self._check_threshold(profitability_percent)

    def _update_profitability_by_time(self, profitability_percent):
        self.profitability_by_time[int(time.time())] = profitability_percent
        current_time = time.time()
        for profitability_time in list(self.profitability_by_time):
            if profitability_time - current_time > self.time_period:
                self.profitability_by_time.pop(profitability_time)

    def _check_threshold(self, profitability_percent):
        oldest_compared_profitability = next(iter(self.profitability_by_time.values()))
        if trading_constants.ZERO < self.percent_change <= profitability_percent - oldest_compared_profitability:
            # profitability_percent reached or when above self.percent_change
            self.trigger(description=f"Profitability reached {self.percent_change}%")
        if trading_constants.ZERO > self.percent_change >= profitability_percent - oldest_compared_profitability:
            # profitability_percent reached or when bellow self.percent_change
            self.trigger(description=f"Profitability reached {self.percent_change}%")

    @staticmethod
    def get_description() -> str:
        return "Will trigger when profitability reaches the given % change on the given time window. " \
               "Example: a Percent change of 10 will trigger the automation if your OctoBot profitability " \
               "changes from 0 to 10 or from 30 to 40."

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        return {
            self.PERCENT_CHANGE: UI.user_input(
                self.PERCENT_CHANGE, commons_enums.UserInputTypes.FLOAT, 35, inputs,
                title="Percent change: minimum change of % profitability to trigger the automation. "
                      "Can be negative to trigger on losses.",
                parent_input_name=step_name,
            ),
            self.TIME_PERIOD: UI.user_input(
                self.TIME_PERIOD, commons_enums.UserInputTypes.FLOAT, 300, inputs,
                title="Time period: maximum time to consider to compute profitability changes. In minutes.",
                parent_input_name=step_name,
            ),
            self.MAX_TRIGGER_FREQUENCY: UI.user_input(
                self.MAX_TRIGGER_FREQUENCY, commons_enums.UserInputTypes.FLOAT, 0.0, inputs,
                title="Maximum trigger frequency: required time between each trigger. In seconds. "
                      "Useful to avoid spamming in certain situations.",
                parent_input_name=step_name,
            ),
            self.TRIGGER_ONLY_ONCE: UI.user_input(
                self.TRIGGER_ONLY_ONCE, commons_enums.UserInputTypes.BOOLEAN, False, inputs,
                title="Trigger only once: can only trigger once until OctoBot restart or "
                      "the automation configuration changes.",
                parent_input_name=step_name,
            ),
        }

    def apply_config(self, config):
        self.clear_future()
        self.profitability_by_time = sortedcontainers.SortedDict()
        self.percent_change = decimal.Decimal(str(config[self.PERCENT_CHANGE]))
        self.time_period = config[self.TIME_PERIOD] * commons_constants.MINUTE_TO_SECONDS
        self.trigger_only_once = config[self.TRIGGER_ONLY_ONCE]
        self.max_trigger_frequency = config[self.MAX_TRIGGER_FREQUENCY]
