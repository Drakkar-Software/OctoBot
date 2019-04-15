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

from typing import Dict

from core.consumers_producers.consumer import Consumer
from core.consumers_producers.producers import Producer

"""
A ConsumerProducer aggregates the data from multiple consumers queue to one final producer.
"""


class ConsumersProducer:
    def __init__(self):
        self.producer: Producer = None
        self.consumers: Dict[Consumer] = {}

    async def start(self):
        for consumer in [consumer.values() for consumer in self.consumers.values()]:
            await consumer.start()
        await self.producer.start()

    async def stop(self):
        for consumer in [consumer.values() for consumer in self.consumers.values()]:
            await consumer.stop()
        await self.producer.stop()

    async def run(self):
        for consumer in [consumer.values() for consumer in self.consumers.values()]:
            await consumer.run()
        await self.producer.run()

    def get_consumer_queue(self) -> ValuesView:
        return self.consumers.values()

    def subscribe_to_producer(self, consumer: Consumer, **kwargs):
        self.producer.add_consumer(consumer)
