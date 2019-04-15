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

from typing import Dict, ValuesView

from core.consumers_producers.consumer import Consumer
from core.consumers_producers.producers import Producer

"""
A ConsumersProducers is an equivalent of a big dispatcher, its handles data from multiple subscribed source 
from multiple consumer queues. It will then dispatch the data through multiple producers.
"""


class ConsumersProducers:
    def __init__(self):
        self.producers: Dict[Producer] = {}
        self.consumers: Dict[Consumer] = {}

    async def start(self):
        for consumer in [consumer.values() for consumer in self.consumers.values()]:
            await consumer.start()
        for producer in [producer.values() for producer in self.producers.values()]:
            await producer.start()

    async def stop(self):
        for consumer in [consumer.values() for consumer in self.consumers.values()]:
            await consumer.stop()
        for producer in [producer.values() for producer in self.producers.values()]:
            await producer.stop()

    async def run(self):
        for consumer in [consumer.values() for consumer in self.consumers.values()]:
            await consumer.run()
        for producer in [producer.values() for producer in self.producers.values()]:
            await producer.run()

    def get_consumer_queue(self) -> ValuesView:
        return self.consumers.values()

    def subscribe_to_producer(self, consumer: Consumer, **kwargs):
        for producer in [producer.values() for producer in self.producers.values()]:
            producer.add_consumer(consumer)
