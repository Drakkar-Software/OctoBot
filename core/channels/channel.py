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
from abc import abstractmethod, ABCMeta
from typing import Dict, List, Iterable

from core.channels import CallbackType
from core.consumer import Consumer
from core.producer import Producer

"""
A Channel ****
"""


class Channel:
    __metaclass__ = ABCMeta

    CHANNEL_NAMES_SEPARATORS = "#"

    def __init__(self):
        self.producer: Producer = None
        self.consumers: Dict[Consumer] = {}

    @classmethod
    def get_name(cls):
        return cls.__name__.replace('Channel', '')

    @abstractmethod
    async def new_consumer(self, callback: CallbackType, size=0, **kwargs):
        """
        Create an appropriate consumer instance for this channel
        :param callback: method that should be called when consuming the queue
        :param size: queue size, default 0
        :return: a new consumer instance
        """
        raise NotImplemented("new consumer is not implemented")

    def get_consumers(self, **kwargs) -> Iterable[Consumer]:
        """
        Should be overwritten according to the class needs
        :param kwargs:
        :return:
        """
        return self.consumers

    async def start(self):
        for consumer in [consumer.values() for consumer in self.consumers.values()]:
            await consumer.start()

        if self.producer:
            await self.producer.start()

    async def stop(self):
        for consumer in [consumer.values() for consumer in self.consumers.values()]:
            await consumer.stop()

        if self.producer:
            await self.producer.stop()

    async def run(self):
        for consumer in [consumer.values() for consumer in self.consumers.values()]:
            await consumer.run()

        if self.producer:
            await self.producer.run()

    @staticmethod
    def create_channel_name(params: List):
        return Channel.CHANNEL_NAMES_SEPARATORS.join(params)
