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
import asyncio
import decimal

import async_channel.enums as channel_enums
import octobot_commons.enums as commons_enums
import octobot_commons.configuration as configuration
import octobot_commons.channels_name as channels_name
import octobot.automation.bases.abstract_trigger_event as abstract_trigger_event
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.api as trading_api


class PriceThreshold(abstract_trigger_event.AbstractTriggerEvent):
    TARGET_PRICE = "target_price"
    SYMBOL = "symbol"
    TRIGGER_ONLY_ONCE = "trigger_only_once"
    MAX_TRIGGER_FREQUENCY = "max_trigger_frequency"

    def __init__(self):
        super().__init__()
        self.waiter_task = None
        self.symbol = None
        self.target_price = None
        self.last_price = None
        self.trigger_event = asyncio.Event()
        self.registered_consumer = False
        self.consumers = []

    async def _register_consumer(self):
        self.registered_consumer = True
        for exchange_id in trading_api.get_exchange_ids():
            self.consumers.append(
                await exchanges_channel.get_chan(
                    channels_name.OctoBotTradingChannelsName.MARK_PRICE_CHANNEL.value,
                    exchange_id
                ).new_consumer(
                    self.mark_price_callback,
                    priority_level=channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value,
                    symbol=self.symbol
                )
            )

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
            self.trigger_event.set()

    async def stop(self):
        await super().stop()
        if self.waiter_task is not None and not self.waiter_task.done():
            self.waiter_task.cancel()
        for consumer in self.consumers:
            await consumer.stop()
        self.consumers = []

    async def _get_next_event(self):
        if self.should_stop:
            raise StopIteration
        if not self.registered_consumer:
            await self._register_consumer()
        self.waiter_task = asyncio.create_task(asyncio.wait_for(self.trigger_event.wait(), timeout=None))
        await self.waiter_task
        self.trigger_event.clear()

    @staticmethod
    def get_description() -> str:
        return "Will trigger when the price of the given symbol crosses the given price."

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
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
        self.trigger_event.clear()
        self.last_price = None
        self.symbol = config[self.SYMBOL]
        self.target_price = decimal.Decimal(str(config[self.TARGET_PRICE]))
        self.trigger_only_once = config[self.TRIGGER_ONLY_ONCE]
        self.max_trigger_frequency = config[self.MAX_TRIGGER_FREQUENCY]
