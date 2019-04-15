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
import asyncio

from typing import Dict

from core.consumers_producers.consumer import Consumer
from core.consumers_producers.producers import Producer

"""
A ConsumerProducers is an equivalent of a dispatcher, it handles data from one/multiple subscribed source/s 
and dispatch to multiple producers
"""


class ConsumerProducers:
    def __init__(self):
        self.producers: Dict[Producer] = {}
        self.consumer: Consumer = None

    async def start(self):
        await self.consumer.start()
        for producer in [producer.values() for producer in self.producers.values()]:
            await producer.start()

    async def stop(self):
        await self.consumer.stop()
        for producer in [producer.values() for producer in self.producers.values()]:
            await producer.stop()

    async def run(self):
        await self.consumer.run()
        for producer in [producer.values() for producer in self.producers.values()]:
            await producer.run()

    def get_consumer_queue(self) -> asyncio.Queue:
        return self.consumer.queue

    def subscribe_to_producer(self, consumer: Consumer, **kwargs):
        for producer in [producer.values() for producer in self.producers.values()]:
            producer.add_consumer(consumer)
