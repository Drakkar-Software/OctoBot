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

import async_channel
import async_channel.enums as channel_enums
import octobot_commons.enums as commons_enums
import octobot_commons.configuration as configuration
import octobot_commons.channels_name as channels_name
import octobot_trading.exchange_channel as exchanges_channel
import octobot.automation.bases.abstract_channel_based_trigger_event as abstract_channel_based_trigger_event

class PriceThreshold(abstract_channel_based_trigger_event.AbstractChannelBasedTriggerEvent):
    TARGET_PRICE = "target_price"
    SYMBOL = "symbol"
    TRIGGER_ONLY_ONCE = "trigger_only_once"
    MAX_TRIGGER_FREQUENCY = "max_trigger_frequency"

    def __init__(self):
        super().__init__()
        # config
        self.target_price: decimal.Decimal = None # type: ignore
        self.last_price: decimal.Decimal = None # type: ignore

    async def register_consumers(self, exchange_id: str) -> list[async_channel.Consumer]:
        return [
            await exchanges_channel.get_chan(
                channels_name.OctoBotTradingChannelsName.MARK_PRICE_CHANNEL.value, exchange_id
            ).new_consumer(
                self.mark_price_callback,
                priority_level=channel_enums.ChannelConsumerPriorityLevels.HIGH.value,
            )
        ]

    async def mark_price_callback(
        self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, mark_price
    ):
        if self.should_stop:
            # do not go any further if the action has been stopped
            return
        self._check_threshold(mark_price)
        self._update_last_price(mark_price)

    def _update_last_price(self, mark_price):
        self.last_price = mark_price

    def _check_threshold(self, mark_price):
        if self.last_price is None:
            return
        if mark_price >= self.target_price > self.last_price or mark_price <= self.target_price < self.last_price:
            # mark_price crossed self.target_price threshold
            self.trigger(description=f"Price crossed {self.target_price} threshold")

    @staticmethod
    def get_description() -> str:
        return "Will trigger when the price of the given symbol crosses the given price."

    def get_user_inputs(
        self, UI: configuration.UserInputFactory, inputs: dict, step_name: str
    ) -> dict:
        return {
            self.SYMBOL: UI.user_input(
                self.SYMBOL, commons_enums.UserInputTypes.TEXT, "BTC/USDT", inputs,
                title="Symbol: symbol to watch price on. Example: ETH/BTC or BTC/USDT:USDT",
                parent_input_name=step_name,
            ),
            self.TARGET_PRICE: UI.user_input(
                self.TARGET_PRICE, commons_enums.UserInputTypes.FLOAT, 300, inputs,
                title="Target price: price triggering the event.",
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
        self.last_price = None # type: ignore
        self.symbol = config[self.SYMBOL]
        self.target_price = decimal.Decimal(str(config[self.TARGET_PRICE]))
        self.trigger_only_once = config[self.TRIGGER_ONLY_ONCE]
        self.max_trigger_frequency = config[self.MAX_TRIGGER_FREQUENCY]
