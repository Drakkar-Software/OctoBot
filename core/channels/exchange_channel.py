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
from abc import ABCMeta, abstractmethod
from typing import List

from config import CONSUMER_CALLBACK_TYPE, CONFIG_WILDCARD
from core.channels.channel import Channel, Channels
from core.channels.channel_instances import ChannelInstances


class ExchangeChannel(Channel):
    __metaclass__ = ABCMeta

    FILTER_SIZE = 1

    def __init__(self, exchange_manager):
        super().__init__()
        self.exchange_manager = exchange_manager
        self.exchange = exchange_manager.exchange

        self.filter_send_counter: int = 0
        self.should_send_filter: bool = False

    @abstractmethod
    async def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, **kwargs):
        raise NotImplemented("new consumer is not implemented")

    def will_send(self):
        self.filter_send_counter += 1

    def has_send(self):
        if self.should_send_filter:
            self.filter_send_counter = 0
            self.should_send_filter = False

    def get_consumers(self, symbol=CONFIG_WILDCARD) -> List:
        try:
            self.should_send_filter: bool = self.filter_send_counter >= self.FILTER_SIZE
            return [consumer
                    for consumer in self.consumers[symbol]
                    if not consumer.filter_size or self.should_send_filter]
        except KeyError:
            self._init_consumer_if_necessary(self.consumers, symbol)
            return self.consumers[symbol]

    def get_consumers_by_timeframe(self, time_frame, symbol=CONFIG_WILDCARD) -> List:
        try:
            should_send_filter: bool = self.filter_send_counter >= self.FILTER_SIZE
            if should_send_filter:
                self.filter_send_counter = 0
            return [consumer
                    for consumer in self.consumers[symbol][time_frame]
                    if not consumer.filter_size or should_send_filter]
        except KeyError:
            self._init_consumer_if_necessary(self.consumers, symbol)
            self._init_consumer_if_necessary(self.consumers[symbol], time_frame)
            return self.consumers[symbol][time_frame]

    def _add_new_consumer_and_run(self, consumer, symbol=None, time_frame=None):
        if symbol:
            # create dict and list if required
            self._init_consumer_if_necessary(self.consumers, symbol)

            if time_frame:
                # create dict and list if required
                self._init_consumer_if_necessary(self.consumers[symbol], time_frame)
                self.consumers[symbol][time_frame].append(consumer)
            else:
                self.consumers[symbol].append(consumer)
        else:
            self.consumers = [consumer]
        consumer.run()
        self.logger.info(f"Consumer started for symbol {symbol}")

    @staticmethod
    def _init_consumer_if_necessary(consumer_list, key):
        if key not in consumer_list:
            consumer_list[key] = []


class ExchangeChannels(Channels):
    @staticmethod
    def set_chan(chan: ExchangeChannel, name: str = None):
        chan_name = chan.get_name() if name else name

        try:
            exchange_chan = ChannelInstances.instance().channels[chan.exchange_manager.exchange.get_name()]
        except KeyError:
            ChannelInstances.instance().channels[chan.exchange_manager.exchange.get_name()] = {}
            exchange_chan = ChannelInstances.instance().channels[chan.exchange_manager.exchange.get_name()]

        if chan_name not in exchange_chan:
            exchange_chan[chan_name] = chan
        else:
            raise ValueError(f"Channel {chan_name} already exists.")

    @staticmethod
    def get_chan(chan_name: str, exchange_name: str = None) -> ExchangeChannel:
        return ChannelInstances.instance().channels[exchange_name][chan_name]
