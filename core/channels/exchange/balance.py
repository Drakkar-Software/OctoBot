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
import asyncio
from asyncio import CancelledError

from config import CONSUMER_CALLBACK_TYPE, CONFIG_WILDCARD
from core.channels.exchange_channel import ExchangeChannel
from core.consumer import Consumer
from core.producer import Producer


class BalanceProducer(Producer):
    async def push(self, balance):
        await self.perform(balance)

    async def perform(self, balance):
        try:
            # if personnal_data.portfolio_is_initialized()
            self.channel.exchange_manager.get_personal_data().set_portfolio(balance)  # TODO check if full or just update
            await self.send(balance)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def send(self, balance):
        for consumer in self.channel.get_consumers():
            consumer.queue.put({
                "balance": balance
            })


class BalanceConsumer(Consumer):
    async def consume(self):
        while not self.should_stop:
            try:
                data = await self.queue.get()
                await self.callback(balance=data["balance"])
            except Exception as e:
                self.logger.exception(f"Exception when calling callback : {e}")


class BalanceChannel(ExchangeChannel):
    def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, size: int = 0):
        self._add_new_consumer_and_run(BalanceConsumer(callback, size=size))
