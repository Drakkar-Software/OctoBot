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
Define async_channel project
"""

from async_channel import constants
from async_channel.constants import (
    CHANNEL_WILDCARD,
    DEFAULT_QUEUE_SIZE,
)

from async_channel import enums
from async_channel.enums import ChannelConsumerPriorityLevels

from async_channel import producer
from async_channel.producer import Producer

from async_channel import consumer
from async_channel.consumer import (
    Consumer,
    InternalConsumer,
    SupervisedConsumer,
)

PROJECT_NAME = "async-channel"
VERSION = "2.2.2"  # major.minor.revision

__all__ = [
    "CHANNEL_WILDCARD",
    "DEFAULT_QUEUE_SIZE",
    "ChannelConsumerPriorityLevels",
    "Producer",
    "Consumer",
    "InternalConsumer",
    "SupervisedConsumer",
    "PROJECT_NAME",
    "VERSION",
]
