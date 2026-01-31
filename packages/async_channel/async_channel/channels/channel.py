# pylint: disable=too-many-positional-arguments
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
Defines the channel core class : Channel
"""
import typing

import async_channel.util.logging_util as logging
import async_channel.enums
import async_channel.channels.channel_instances as channel_instances

if typing.TYPE_CHECKING:
    import async_channel.producer


# pylint: disable=undefined-variable, not-callable
class Channel:
    """
    A Channel is the object to connect a producer / producers class(es) to a consumer / consumers class(es)
    It contains a registered consumers dict to notify every consumer when a producer 'send' something.
    It contains a registered producers list to allow producer modification through 'modify'.
    To access channels a 'Channels' singleton is created to manage instances.
    """

    # Channel producer class
    PRODUCER_CLASS: typing.Optional[typing.Type["async_channel.producer.Producer"]] = (
        None
    )

    # Channel consumer class
    CONSUMER_CLASS: typing.Optional[typing.Type["async_channel.consumer.Consumer"]] = (
        None
    )

    # Consumer instance in consumer filters
    INSTANCE_KEY = "consumer_instance"

    # Channel default consumer priority level
    DEFAULT_PRIORITY_LEVEL = (
        async_channel.enums.ChannelConsumerPriorityLevels.HIGH.value
    )

    def __init__(self):
        self.logger = logging.get_logger(self.__class__.__name__)

        # Channel unique id
        self.chan_id: typing.Optional[str] = None

        # Channel subscribed producers list
        self.producers: list["async_channel.producer.Producer"] = []

        # Channel subscribed consumers list: list dicts of dicts containing:
        # - At least a consumer instance under the INSTANCE_KEY key
        # - Possibly other filters under other keys and values
        self.consumers: list[dict[str, typing.Any]] = []

        # Used to perform global send from non-producer context
        self.internal_producer: typing.Optional["async_channel.producer.Producer"] = (
            None
        )

        # Used to save producers state (paused or not)
        self.is_paused: bool = True

        # Used to synchronize producers and consumer
        self.is_synchronized: bool = False

    @classmethod
    def get_name(cls) -> str:
        """
        Default implementation is to return the name of the class without the 'Channel' substring
        :returns the channel name
        """
        return cls.__name__.replace("Channel", "")

    # pylint: disable=too-many-arguments
    async def new_consumer(
        self,
        callback: object = None,
        consumer_filters: typing.Optional[dict] = None,
        internal_consumer: typing.Optional["async_channel.consumer.Consumer"] = None,
        size: int = 0,
        priority_level: int = DEFAULT_PRIORITY_LEVEL,
    ) -> "async_channel.consumer.Consumer":
        """
        Create an appropriate consumer instance for this async_channel and add it to the consumer list
        Should end by calling '_check_producers_state'
        :param callback: method that should be called when consuming the queue
        :param consumer_filters: the consumer filters
        :param size: queue size, default 0
        :param priority_level: used by Producers the lowest level has the highest priority
        :param internal_consumer: internal consumer instance to use if specified
        :return: consumer instance created
        """
        consumer = (
            internal_consumer
            if internal_consumer
            else self.CONSUMER_CLASS(callback, size=size, priority_level=priority_level)  # type: ignore
        )
        await self._add_new_consumer_and_run(consumer, consumer_filters)
        await self._check_producers_state()
        return consumer

    # pylint: disable=unused-argument
    async def _add_new_consumer_and_run(
        self,
        consumer: "async_channel.consumer.Consumer",
        consumer_filters: typing.Optional[dict],
        **kwargs,
    ) -> None:
        """
        Should be called by 'new_consumer' to add the consumer to self.consumers and call 'consumer.run()'
        :param consumer: the consumer to add
        :param kwargs: additional params for consumer list
        :return: None
        """
        if consumer_filters is None:
            consumer_filters = {}

        self.add_new_consumer(consumer, consumer_filters)
        await consumer.run(with_task=not self.is_synchronized)

    def add_new_consumer(
        self, consumer: "async_channel.consumer.Consumer", consumer_filters: dict
    ) -> None:
        """
        Add a new consumer to consumer list with filters
        :param consumer: the consumer to add
        :param consumer_filters: the consumer selection filters (used by 'get_consumer_from_filters')
        :return: None
        """
        consumer_filters[self.INSTANCE_KEY] = consumer
        self.consumers.append(consumer_filters)

    def get_consumer_from_filters(
        self, consumer_filters: dict
    ) -> list["async_channel.consumer.Consumer"]:
        """
        Returns the instance filtered consumers list
        WARNING:
            >>> get_consumer_from_filters({"A": 1})
            Can return a consumer described by {"A": True} because in python 1 == True
        :param consumer_filters: The consumer filters dict
        :return: the filtered consumer list
        """
        return self._filter_consumers(consumer_filters)

    def get_consumers(self) -> list["async_channel.consumer.Consumer"]:
        """
        Returns all consumers instance
        Can be overwritten according to the class needs
        :return: the subscribed consumers list
        """
        return [consumer[self.INSTANCE_KEY] for consumer in self.consumers]

    def get_prioritized_consumers(
        self, priority_level: int
    ) -> list["async_channel.consumer.Consumer"]:
        """
        Returns all consumers instance
        Can be overwritten according to the class needs
        :return: the subscribed consumers list
        """
        return [
            consumer[self.INSTANCE_KEY]
            for consumer in self.consumers
            if consumer[self.INSTANCE_KEY].priority_level <= priority_level
        ]

    def _filter_consumers(
        self, consumer_filters: dict
    ) -> list["async_channel.consumer.Consumer"]:
        """
        Returns the consumers that match the selection
        Returns all consumer instances if consumer_filter is empty
        :param consumer_filters: listed consumer filters
        :return: the list of the filtered consumers
        """
        return [
            consumer[self.INSTANCE_KEY]
            for consumer in self.consumers
            if _check_filters(consumer, consumer_filters)
        ]

    async def remove_consumer(
        self, consumer: "async_channel.consumer.Consumer"
    ) -> None:
        """
        Should be overwritten according to the class needs
        Should end by calling '_check_producers_state' and then 'consumer.stop'
        :param consumer: consumer instance to remove from consumers list
        """
        for consumer_candidate in self.consumers:
            if consumer == consumer_candidate[self.INSTANCE_KEY]:
                self.consumers.remove(consumer_candidate)
                await self._check_producers_state()
                await consumer.stop()

    async def _check_producers_state(self) -> None:
        """
        Checks if producers should be paused or resumed after a consumer addition or removal
        """
        if self._should_pause_producers():
            self.is_paused = True
            for producer in self.get_producers():
                await producer.pause()
            return
        if self._should_resume_producers():
            self.is_paused = False
            for producer in self.get_producers():
                await producer.resume()

    def _should_pause_producers(self) -> bool:
        """
        Check if channel producers should be paused
        :return: True if channel producers should be paused
        """
        if self.is_paused:
            return False
        if not self.get_consumers():
            return True
        for consumer in self.get_consumers():
            if (
                consumer.priority_level
                < async_channel.ChannelConsumerPriorityLevels.OPTIONAL.value
            ):
                return False
        return True

    def _should_resume_producers(self) -> bool:
        """
        Check if channel producers should be resumed
        :return: True if channel producers should be resumed
        """
        if not self.is_paused:
            return False
        if not self.get_consumers():
            return False
        for consumer in self.get_consumers():
            if (
                consumer.priority_level
                < async_channel.ChannelConsumerPriorityLevels.OPTIONAL.value
            ):
                return True
        return False

    async def register_producer(
        self, producer: "async_channel.producer.Producer"
    ) -> None:
        """
        Add the producer to producers list
        Can be overwritten to perform additional action when registering
        Should end by calling 'pause' if self.is_paused
        :param Producer producer: created channel producer to register
        """
        if producer not in self.producers:
            self.producers.append(producer)

        if self.is_paused:
            await producer.pause()

    def unregister_producer(self, producer: "async_channel.producer.Producer") -> None:
        """
        Remove the producer from producers list
        Can be overwritten to perform additional action when registering
        :param Producer producer: created channel producer to unregister
        """
        if producer in self.producers:
            self.producers.remove(producer)

    def get_producers(self) -> typing.Iterable["async_channel.producer.Producer"]:
        """
        Should be overwritten according to the class needs
        :return: async_channel producers iterable
        """
        return self.producers

    async def start(self) -> None:
        """
        Call each registered consumers start method
        """
        for consumer in self.get_consumers():
            await consumer.start()

    async def stop(self) -> None:
        """
        Call each registered consumers and producers stop method
        """
        for consumer in self.get_consumers():
            await consumer.stop()

        for producer in self.get_producers():
            await producer.stop()

        if self.internal_producer is not None:
            await self.internal_producer.stop()

    def flush(self) -> None:
        """
        Flush the channel object before stopping
        """
        if self.internal_producer is not None:
            self.internal_producer.channel = None
        for producer in self.get_producers():
            producer.channel = None

    async def run(self) -> None:
        """
        Call each registered consumers run method
        """
        for consumer in self.get_consumers():
            await consumer.run(with_task=not self.is_synchronized)

    async def modify(self, **kwargs) -> None:
        """
        Call each registered producers modify method
        """
        for producer in self.get_producers():
            await producer.modify(**kwargs)

    def get_internal_producer(self, **kwargs) -> "async_channel.producer.Producer":
        """
        Returns internal producer if exists else creates it
        :param kwargs: arguments for internal producer __init__
        :return: internal producer instance
        """
        if not self.internal_producer:
            try:
                self.internal_producer = self.PRODUCER_CLASS(self, **kwargs)  # type: ignore
            except TypeError:
                self.logger.exception("PRODUCER_CLASS not defined")
                raise
        return self.internal_producer


def set_chan(chan: Channel, name: str) -> Channel:
    """
    Set a new Channel instance in the channels list according to channel name
    :param chan: new Channel instance
    :param name: name of the channel
    :return: the channel instance if succeed else raise a ValueError
    """
    chan_name = name if name else chan.get_name()
    if chan_name not in channel_instances.ChannelInstances.instance().channels:
        channel_instances.ChannelInstances.instance().channels[chan_name] = chan
        return chan
    raise ValueError(f"Channel {chan_name} already exists.")


def del_chan(name: str) -> None:
    """
    Delete a Channel instance from the channels list according to channel name
    :param name: name of the channel to delete
    """
    if name in channel_instances.ChannelInstances.instance().channels:
        channel_instances.ChannelInstances.instance().channels.pop(name, None)


def get_chan(chan_name: str) -> Channel:
    """
    Return the channel instance from channel name
    :param chan_name: the channel name
    :return: the Channel instance
    """
    return channel_instances.ChannelInstances.instance().channels[chan_name]


def _check_filters(consumer_filters: dict, expected_filters: dict) -> bool:
    """
    Checks if the consumer match the specified filters
    Returns True if expected_filters is empty
    :param consumer_filters: consumer filters
    :param expected_filters: selected filters
    :return: True if the consumer match the selection, else False
    """
    try:
        for key, value in expected_filters.items():
            if value == async_channel.CHANNEL_WILDCARD:
                continue
            if isinstance(consumer_filters[key], list):
                if set(consumer_filters[key]) & {value, async_channel.CHANNEL_WILDCARD}:
                    continue
                return False
            if consumer_filters[key] not in [value, async_channel.CHANNEL_WILDCARD]:
                return False
        return True
    except KeyError:
        return False
