#  Drakkar-Software OctoBot-Services
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
import abc

import async_channel.channels as channels
import async_channel.producer as producer
import async_channel.consumer as consumer


class AbstractServiceFeedChannelConsumer(consumer.Consumer):
    __metaclass__ = abc.ABCMeta


class AbstractServiceFeedChannelProducer(producer.Producer):
    __metaclass__ = abc.ABCMeta


class AbstractServiceFeedChannel(channels.Channel):
    __metaclass__ = abc.ABCMeta

    PRODUCER_CLASS = AbstractServiceFeedChannelProducer
    CONSUMER_CLASS = AbstractServiceFeedChannelConsumer
