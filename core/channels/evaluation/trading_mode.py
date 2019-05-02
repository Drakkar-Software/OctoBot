#  Drakkar-Software OctoBot
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

"""
Handles strategy evaluations
"""
from asyncio import CancelledError

from config import CONSUMER_CALLBACK_TYPE
from core.channels.exchange_channel import ExchangeChannel
from core.consumer import Consumer
from core.producer import Producer


class TradingModeProducer(Producer):
    async def push(self, strategy_evaluation):
        # TODO replace queue content
        await self.perform(strategy_evaluation)

    async def perform(self, strategy_evaluation):
        try:
            await self.send(strategy_evaluation)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def send(self, strategy_evaluation):
        if self.channel.consumer:
            await self.channel.consumer.queue.put({"stgy_eval": strategy_evaluation})


class TradingModeConsumer(Consumer):
    async def consume(self):
        while not self.should_stop:
            try:
                data = await self.queue.get()
                await self.callback(strategy_evaluation=data["stgy_eval"])
            except Exception as e:
                self.logger.exception(f"Exception when calling callback : {e}")


class TradingModeChannel(ExchangeChannel):
    def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, size: int = 1):
        self._add_new_consumer_and_run(TradingModeConsumer(callback, size=size))
