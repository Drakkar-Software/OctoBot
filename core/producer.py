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
from abc import ABCMeta
from asyncio import Task
from typing import Iterable

from core.consumer import Consumer
from tools import get_logger


class Producer:
    __metaclass__ = ABCMeta

    def __init__(self, channel):
        self.channel = channel
        self.logger = get_logger(self.__class__.__name__)

        # List of consumer queues to be fill
        self.consumers: Iterable[Consumer] = None
        self.produce_task: Task = None
        self.should_stop: bool = False

    async def send(self, **kwargs):
        """
        Send to each consumer data though its queue
        :param data:
        :return:
        """
        for consumer in self.consumers:
            await consumer.queue.put(kwargs)

    async def receive(self, **kwargs):
        """
        Receive notification that new data should be sent implementation
        When nothing should be done on data : self.send()
        :return: None
        """
        pass

    async def start(self):
        """
        Should be implemented for producer's non-triggered tasks
        :return: None
        """
        pass

    async def perform(self, **kwargs):
        """
        Should implement producer's non-triggered tasks
        Can be use to force producer to perform tasks
        :return: None
        """
        pass

    async def stop(self):
        """
        Stops non-triggered tasks management
        :return: None
        """
        self.should_stop = True

    def create_task(self):
        self.produce_task = asyncio.create_task(self.start())

    async def run(self):
        self.create_task()
