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
Define async_channel Consumer class
"""
import asyncio
import typing

import async_channel.util.logging_util as logging
import async_channel.enums


class Consumer:
    """
    A consumer keeps reading from the channel and processes any data passed to it.
    A consumer will start consuming by calling its 'consume' method.
    The data processing implementation is coded in the 'perform' method.
    A consumer also responds to channel events like pause and stop.
    """

    def __init__(
        self,
        callback: typing.Callable,
        size: int = async_channel.constants.DEFAULT_QUEUE_SIZE,
        priority_level: int = async_channel.enums.ChannelConsumerPriorityLevels.HIGH.value,
    ):
        self.logger = logging.get_logger(self.__class__.__name__)

        # Consumer data queue. It contains producer's work (received through Producer.send()).
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=size)

        # Method to be called when performing task is done
        self.callback: typing.Callable = callback

        # Should only be used with .cancel()
        self.consume_task: typing.Optional[asyncio.Task] = None

        """
        Should be used as the perform while loop condition
            >>> while(self.should_stop):
                    ...
        """
        self.should_stop: bool = False

        # Default priority level
        # Used by Producers to call consumers by prioritization
        # The lowest level has the highest priority
        self.priority_level: int = priority_level

    async def consume(self) -> None:
        """
        Should be overwritten with a self.queue.get() in a while loop
        """
        while not self.should_stop:
            try:
                await self.perform(await self.queue.get())
            except asyncio.CancelledError:
                self.logger.debug("Cancelled task")
            except Exception as consume_exception:  # pylint: disable=broad-except
                self.logger.exception(
                    consume_exception,
                    publish_error_if_necessary=True,  # type: ignore
                    error_message=f"Exception when calling callback on {self}: {consume_exception}",  # type: ignore
                )
            finally:
                await self.consume_ends()

    async def perform(self, kwargs) -> None:
        """
        Should be overwritten to handle queue data
        :param kwargs: queue get content
        """
        await self.callback(**kwargs)

    async def consume_ends(self) -> None:
        """
        Should be overwritten to handle consumption ends
        """

    async def start(self) -> None:
        """
        Should be implemented for consumer's non-triggered tasks
        """
        self.should_stop = False

    async def stop(self) -> None:
        """
        Stops non-triggered tasks management
        """
        self.should_stop = True
        if self.consume_task:
            self.consume_task.cancel()

    def create_task(self) -> None:
        """
        Creates a new asyncio task that contains start() execution
        """
        self.consume_task = asyncio.create_task(self.consume())

    async def run(self, with_task: bool = True) -> None:
        """
        - Initialize the consumer
        - Start the consumer main task
        :param with_task: If the consumer should run in a task
        """
        await self.start()
        if with_task:
            self.create_task()

    async def join(self, timeout: float) -> None:
        """
        Implemented in SupervisedConsumer to wait for any "perform" call to be finished.
        Instantly returns on regular consumer
        """

    async def join_queue(self) -> None:
        """
        Implemented in SupervisedConsumer to wait for the whole queue to finish
        processing.
        Instantly returns on regular consumer
        """

    def __str__(self) -> str:
        return f"{self.__class__.__name__} with callback: {self.callback.__name__}"


class InternalConsumer(Consumer):
    """
    An InternalConsumer is a classic Consumer except that his callback is declared internally
    """

    def __init__(self):
        """
        The constructor only override the callback to be the 'internal_callback' method
        """
        super().__init__(None)
        self.callback: typing.Callable = self.internal_callback

    async def internal_callback(self, **kwargs: dict) -> None:
        """
        The method triggered when the producer has pushed into the channel
        :param kwargs: Additional params
        """
        raise NotImplementedError("internal_callback is not implemented")


class SupervisedConsumer(Consumer):
    """
    A SupervisedConsumer is a classic Consumer that notifies the queue when its work is done
    """

    def __init__(
        self,
        callback: typing.Callable,
        size: int = async_channel.constants.DEFAULT_QUEUE_SIZE,
        priority_level: int = async_channel.enums.ChannelConsumerPriorityLevels.HIGH.value,
    ):
        """
        The constructor only override the callback to be the 'internal_callback' method
        """
        super().__init__(callback, size=size, priority_level=priority_level)

        # Clear when perform is running (set after)
        self.idle: asyncio.Event = asyncio.Event()
        self.idle.set()

    async def join(self, timeout: float) -> None:
        """
        Wait for any perform to be finished.
        """
        if not self.idle.is_set():
            await asyncio.wait_for(self.idle.wait(), timeout)

    async def join_queue(self) -> None:
        """
        Wait for the consumer queue to finish processing.
        """
        await self.queue.join()

    async def perform(self, kwargs) -> None:
        """
        Clear self.idle event when perform is being done then set it
        :param kwargs: queue get content
        """
        try:
            self.idle.clear()
            await self.callback(**kwargs)
        finally:
            self.idle.set()

    async def consume_ends(self) -> None:
        """
        The method called when the work is done
        """
        try:
            self.queue.task_done()
        except (
            ValueError
        ):  # when task_done() is called when the Exception was CancelledError
            pass
