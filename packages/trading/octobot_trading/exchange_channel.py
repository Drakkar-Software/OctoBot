# pylint: disable=E0203, W0237
#  Drakkar-Software OctoBot-Trading
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

import octobot_commons.tree as commons_tree

import async_channel.enums as channel_enums
import async_channel.constants as channel_constants
import async_channel.channels as channels
import async_channel.consumer as consumers
import async_channel.producer as producers

import octobot_commons.logging as logging


class ExchangeChannelConsumer(consumers.Consumer):
    """
    Consumer adapted for ExchangeChannel
    """


class ExchangeChannelInternalConsumer(consumers.InternalConsumer):
    """
    InternalConsumer adapted for ExchangeChannel
    """


class ExchangeChannelSupervisedConsumer(consumers.SupervisedConsumer):
    """
    SupervisedConsumer adapted for ExchangeChannel
    """


class ExchangeChannelProducer(producers.Producer):
    """
    Producer adapted for ExchangeChannel
    """
    CHANNEL_NAME = None
    # set True if this channels should be notified when traded symbols are updated
    TO_NOTIFY_ON_TRADED_SYMBOLS_UPDATE: bool = False

    def __init__(self, channel):
        super().__init__(channel)
        self.logger = logging.get_logger(f"{self.__class__.__name__}[{channel.exchange_manager.exchange_name}]")
        self.single_update_task = None

    async def fetch_and_push(self):
        self.logger.error("self.fetch_and_push() is not implemented")

    def trigger_single_update(self):
        self.single_update_task = asyncio.create_task(self.fetch_and_push())

    async def wait_for_dependencies(self, paths, timeout):
        for path in paths:
            if not await commons_tree.EventProvider.instance().wait_for_event(
                self.channel.exchange_manager.bot_id,
                path,
                timeout
            ):
                return False
        return True


class ExchangeChannel(channels.Channel):
    PRODUCER_CLASS = ExchangeChannelProducer
    CONSUMER_CLASS = ExchangeChannelConsumer
    CRYPTOCURRENCY_KEY = "cryptocurrency"
    SYMBOL_KEY = "symbol"
    DEFAULT_PRIORITY_LEVEL = channel_enums.ChannelConsumerPriorityLevels.HIGH.value

    def __init__(self, exchange_manager):
        super().__init__()
        self.logger = logging.get_logger(f"{self.__class__.__name__}[{exchange_manager.exchange_name}]")
        self.exchange_manager = exchange_manager

        self.filter_send_counter = 0
        self.should_send_filter = False

    async def new_consumer(self,
                           callback: object = None,
                           consumer_instance: object = None,
                           size: int = 0,
                           priority_level: int = DEFAULT_PRIORITY_LEVEL,
                           symbol: str = channel_constants.CHANNEL_WILDCARD,
                           cryptocurrency: str = channel_constants.CHANNEL_WILDCARD,
                           **kwargs) -> ExchangeChannelConsumer:
        consumer = consumer_instance if consumer_instance else self.CONSUMER_CLASS(
            callback, size=size, priority_level=priority_level
        )
        await self._add_new_consumer_and_run(consumer,
                                             cryptocurrency=cryptocurrency,
                                             symbol=symbol,
                                             **kwargs)
        await self._check_producers_state()
        return consumer

    def get_filtered_consumers(self,
                               cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                               symbol=channel_constants.CHANNEL_WILDCARD):
        return self.get_consumer_from_filters({
            self.CRYPTOCURRENCY_KEY: cryptocurrency,
            self.SYMBOL_KEY: symbol
        })

    async def _add_new_consumer_and_run(self, consumer,
                                        cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                                        symbol=channel_constants.CHANNEL_WILDCARD):
        self.add_new_consumer(consumer,
                              {
                                  self.CRYPTOCURRENCY_KEY: cryptocurrency,
                                  self.SYMBOL_KEY: symbol
                              })
        await self._run_consumer(consumer,
                                 symbol=symbol)

    async def _run_consumer(self, consumer,
                            symbol=channel_constants.CHANNEL_WILDCARD):
        await consumer.run(with_task=not self.is_synchronized)
        self.logger.debug(f"Consumer started for symbol {symbol}: {consumer}")


class TimeFrameExchangeChannel(ExchangeChannel):
    TIME_FRAME_KEY = "time_frame"

    def get_filtered_consumers(self,
                               cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                               symbol=channel_constants.CHANNEL_WILDCARD,
                               time_frame=channel_constants.CHANNEL_WILDCARD):
        return self.get_consumer_from_filters({
            self.CRYPTOCURRENCY_KEY: cryptocurrency,
            self.SYMBOL_KEY: symbol,
            self.TIME_FRAME_KEY: time_frame
        })

    async def _add_new_consumer_and_run(self, consumer,
                                        cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                                        symbol=channel_constants.CHANNEL_WILDCARD,
                                        time_frame=channel_constants.CHANNEL_WILDCARD):
        self.add_new_consumer(consumer,
                              {
                                  self.CRYPTOCURRENCY_KEY: cryptocurrency,
                                  self.SYMBOL_KEY: symbol,
                                  self.TIME_FRAME_KEY: time_frame
                              })
        await self._run_consumer(consumer,
                                 symbol=symbol)


def set_chan(chan, name) -> None:
    chan_name = chan.get_name() if name else name

    try:
        exchange_chan = channels.ChannelInstances.instance().channels[chan.exchange_manager.id]
    except KeyError:
        channels.ChannelInstances.instance().channels[chan.exchange_manager.id] = {}
        exchange_chan = channels.ChannelInstances.instance().channels[chan.exchange_manager.id]

    if chan_name not in exchange_chan:
        exchange_chan[chan_name] = chan
    else:
        raise ValueError(f"Channel {chan_name} already exists.")


def get_exchange_channels(exchange_id) -> dict[str, ExchangeChannel]:
    try:
        return channels.ChannelInstances.instance().channels[exchange_id]
    except KeyError as err:
        raise KeyError(f"Channels not found on exchange with id: {exchange_id}") from err


def get_to_notify_on_traded_symbols_update_channels(exchange_id) -> dict[str, ExchangeChannel]:
    return {
        name: channel
        for name, channel in get_exchange_channels(exchange_id).items()
        if (
            isinstance(channel.get_internal_producer(), ExchangeChannelProducer)
            and channel.get_internal_producer().TO_NOTIFY_ON_TRADED_SYMBOLS_UPDATE
        ) or any(
            isinstance(producer, ExchangeChannelProducer) and producer.TO_NOTIFY_ON_TRADED_SYMBOLS_UPDATE 
            for producer in channel.producers
        )
    }

def del_exchange_channel_container(exchange_id):
    try:
        channels.ChannelInstances.instance().channels.pop(exchange_id, None)
    except KeyError as err:
        raise KeyError(f"Channels not found on exchange with id: {exchange_id}") from err


def get_chan(chan_name, exchange_id) -> ExchangeChannel:
    try:
        return channels.ChannelInstances.instance().channels[exchange_id][chan_name]
    except KeyError as err:
        raise KeyError(f"Channel {chan_name} not found on exchange with id: {exchange_id}") from err


def del_chan(chan_name, exchange_id) -> None:
    try:
        channels.ChannelInstances.instance().channels[exchange_id].pop(chan_name, None)
    except KeyError:
        logging.get_logger(ExchangeChannel.__name__).warning(f"Can't del chan {chan_name} "
                                                             f"on exchange with id: {exchange_id}")


async def stop_exchange_channels(exchange_manager, should_warn=True) -> None:
    """
    Stop exchange channels and producers
    :param exchange_manager: the related exchange manager
    :param should_warn: if an error message should be logged if an error happened during stopping process
    """
    try:
        for channel_name in list(get_exchange_channels(exchange_manager.id)):
            channel = get_chan(channel_name, exchange_manager.id)
            await channel.stop()
            for consumer in channel.consumers:
                await channel.remove_consumer(consumer)
            get_chan(channel_name, exchange_manager.id).flush()
            del_chan(channel_name, exchange_manager.id)
        del_exchange_channel_container(exchange_manager.id)
    except KeyError:
        if should_warn:
            exchange_manager.logger.error(f"No exchange channel for this exchange (id: {exchange_manager.id})")
