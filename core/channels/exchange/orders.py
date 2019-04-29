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
from asyncio import CancelledError

from typing import List

from config import CONSUMER_CALLBACK_TYPE, CONFIG_WILDCARD
from core.channels.exchange.exchange_channel import ExchangeChannel
from core.consumer import Consumer
from core.producer import Producer


class OrdersProducer(Producer):
    def __init__(self, channel: ExchangeChannel):
        super().__init__(channel)

    async def receive(self, symbol, order):
        await self.perform(symbol, order)

    async def perform(self, symbol, order):
        try:
            if symbol in self.channel.consumers:  # and personnal_data.orders_are_initialized()
                self.channel.exchange_manager.get_personal_data(symbol).upsert_order(order.id, order)  # TODO check if exists
                await self.send(symbol, order)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def send(self, symbol, order):
        for consumer in self.channel.get_consumers(symbol=symbol):
            await consumer.queue.put({
                "symbol": symbol,
                "order": order
            })


class OrdersConsumer(Consumer):
    def __init__(self, callback: CONSUMER_CALLBACK_TYPE):
        super().__init__(callback)

    async def consume(self):
        while not self.should_stop:
            try:
                data = await self.queue.get()
                await self.callback(symbol=data["symbol"], order=data["order"])
            except Exception as e:
                self.logger.exception(f"Exception when calling callback : {e}")


class OrdersChannel(ExchangeChannel):
    def __init__(self, exchange_manager):
        super().__init__(exchange_manager)

    def get_consumers(self, symbol) -> List:
        if symbol not in self.consumers:
            self.consumers[symbol] = []

        return self.consumers[symbol] + self.consumers[CONFIG_WILDCARD]

    def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, size=0, symbol=CONFIG_WILDCARD):
        # create dict and list if required
        consumer = OrdersConsumer(callback)
        self.consumers[symbol].append(consumer)
        consumer.run()
