#  Drakkar-Software Async-Channel
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
Define async_channel Producer class
"""
import asyncio
import typing

import async_channel.util.logging_util as logging

if typing.TYPE_CHECKING:
    import async_channel.channels.channel


class Producer:
    """
    A Producer is responsible for producing some output that may be placed onto the head of a queue.
    A Consumer will consume this data through the same shared queue.
    A producer doesn't need to know or care about its consumers.
    But if there is no space in the queue, it won't be able to share what it has produced.
    It manages its consumer calls by priority levels
    When the channel is synchronized priority levels are used to priorities or delay consumer calls
    """

    def __init__(self, channel: "async_channel.channels.channel.Channel"):
        self.logger = logging.get_logger(self.__class__.__name__)

        # Related async_channel instance
        self.channel: "async_channel.channels.channel.Channel" = channel

        """
        Should only be used with .cancel()
        """
        self.produce_task: typing.Optional[asyncio.Task] = None

        """
        Should be used as the perform while loop condition
            while(self.should_stop):
                ...
        """
        self.should_stop: bool = False

        """
        Should be used to know if the producer is already started
        """
        self.is_running: bool = False

    async def send(self, data: typing.Any) -> None:
        """
        Send to each consumer data though its queue
        :param data: data to be put into consumers queues

        The implementation should use 'self.async_channel.get_consumers'
        Example
            >>> for consumer in self.async_channel.get_consumers():
            >>>     await consumer.queue.put({
            >>>         "my_key": my_value
            >>>     })
        """
        for consumer in self.channel.get_consumers():
            await consumer.queue.put(data)

    async def push(self, **kwargs) -> None:
        """
        Push notification that new data should be sent implementation
        When nothing should be done on data : self.send()
        """

    async def start(self) -> None:
        """
        Should be implemented for producer's non-triggered tasks
        """

    async def pause(self) -> None:
        """
        Called when the channel runs out of consumer
        """
        self.logger.debug("Pausing...")
        self.is_running = False
        # Triggers itself if not already paused
        if not self.channel.is_paused:
            self.channel.is_paused = True

    async def resume(self) -> None:
        """
        Called when the channel is no longer out of consumer
        """
        self.logger.debug("Resuming...")
        # Triggers itself if not already resumed
        if self.channel.is_paused:
            self.channel.is_paused = False

    async def perform(self, **kwargs) -> None:
        """
        Should implement producer's non-triggered tasks
        Can be use to force producer to perform tasks
        """

    async def modify(self, **kwargs) -> None:
        """
        Should be implemented when producer can be modified during perform()
        """

    async def wait_for_processing(self) -> None:
        """
        Should be used only with SupervisedConsumers
        It will wait until all consumers have notified that their consume() method have ended
        """
        await asyncio.gather(
            *(consumer.join_queue() for consumer in self.channel.get_consumers())
        )

    async def synchronized_perform_consumers_queue(
        self, priority_level: int, join_consumers: bool, timeout: float
    ) -> None:
        """
        Empties the queue synchronously for each consumers
        :param priority_level: the consumer minimal priority level
        :param join_consumers: True if consumer tasks should be joined. Avoids orphaned tasks to run without
        :param timeout: Time to wait for consumers in join call
        waiting for them when started before this check (when check, their queue is empty but a task is running)
        """
        for consumer in self.channel.get_prioritized_consumers(priority_level):
            while not consumer.queue.empty():
                await consumer.perform(await consumer.queue.get())
            if join_consumers:
                await consumer.join(timeout)

    async def stop(self) -> None:
        """
        Stops non-triggered tasks management
        """
        self.should_stop = True
        self.is_running = False
        if self.produce_task:
            self.produce_task.cancel()

    def create_task(self) -> None:
        """
        Creates a new asyncio task that contains start() execution
        """
        self.is_running = True
        self.produce_task = asyncio.create_task(self.start())

    async def run(self) -> None:
        """
        Start the producer main task
        Shouldn't start the producer main task if the channel is synchronized
        Should always call
        >>> self.async_channel.register_producer
        """
        await self.channel.register_producer(self)
        if not self.channel.is_synchronized:
            self.create_task()

    def is_consumers_queue_empty(self, priority_level: int) -> bool:
        """
        Check if consumers queue are empty
        :param priority_level: the consumer minimal priority level
        :return: the check result
        """
        for consumer in self.channel.get_consumers():
            if consumer.priority_level <= priority_level and not consumer.queue.empty():
                return False
        return True
