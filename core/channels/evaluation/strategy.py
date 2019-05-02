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
Handles matrix changes
"""
from asyncio import CancelledError

from config import CONSUMER_CALLBACK_TYPE
from core.channels.exchange_channel import ExchangeChannel
from core.consumer import Consumer
from core.producer import Producer


class StrategyProducer(Producer):
    async def push(self, evaluation):
        await self.perform(evaluation)

    async def perform(self, evaluation):
        try:
            await self.send(evaluation)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def send(self, evaluation):
        if self.channel.consumer:
            await self.channel.consumer.queue.put({"evaluation": evaluation})


class StrategyConsumer(Consumer):
    async def consume(self):
        while not self.should_stop:
            try:
                data = await self.queue.get()
                await self.callback(evaluation=data["evaluation"])
            except Exception as e:
                self.logger.exception(f"Exception when calling callback : {e}")


class StrategyChannel(ExchangeChannel)
    def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, size=0):
        self._add_new_consumer_and_run(StrategyConsumer(callback, size=size))
