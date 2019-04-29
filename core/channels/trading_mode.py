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
Handles balance changes
"""
from asyncio import CancelledError

from config import CONSUMER_CALLBACK_TYPE
from core.channels.channel import Channel
from core.channels.exchange.exchange_channel import ExchangeChannel
from core.consumer import Consumer
from core.producer import Producer


class TradingModeProducer(Producer):
    def __init__(self, channel: ExchangeChannel):
        super().__init__(channel)

    async def receive(self, matrix):
        await self.perform(matrix)

    async def perform(self, matrix):
        try:
            await self.send(matrix)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def send(self, matrix):
        if self.channel.consumer:
            await self.channel.consumer.queue.put({"matrix": matrix})


class TradingModeConsumer(Consumer):
    def __init__(self, callback: CONSUMER_CALLBACK_TYPE):
        super().__init__(callback)

    async def consume(self):
        while not self.should_stop:
            try:
                data = await self.queue.get()
                await self.callback(matrix=data["matrix"])
            except Exception as e:
                self.logger.exception(f"Exception when calling callback : {e}")


class TradingModeChannel(Channel):
    def __init__(self):
        super().__init__()
        self.consumer: TradingModeConsumer = None

    def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, size=1):
        self.consumer = TradingModeConsumer(callback)
        self.consumer.run()
