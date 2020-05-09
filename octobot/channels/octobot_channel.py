# pylint: disable=E0203
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
from octobot_channels.constants import CHANNEL_WILDCARD

from octobot_channels.channels.channel import Channel
from octobot_channels.consumer import Consumer
from octobot_channels.producer import Producer


class OctoBotChannelConsumer(Consumer):
    """
    Consumer adapted for OctoBotChannel
    """


class OctoBotChannelProducer(Producer):
    """
    Producer adapted for OctoBotChannel
    """
    async def send(self, subject, action, data=None):
        for consumer in self.channel.get_filtered_consumers(subject=subject, action=action):
            await consumer.queue.put({
                "subject": subject,
                "action": action,
                "data": data
            })


class OctoBotChannel(Channel):
    """
    Channel used to communicate OctoBot high level events
    """
    PRODUCER_CLASS = OctoBotChannelProducer
    CONSUMER_CLASS = OctoBotChannelConsumer
    DEFAULT_PRIORITY_LEVEL = 1

    SUBJECT_KEY = "subject"
    ACTION_KEY = "subject"

    def __init__(self, bot_id):
        super().__init__()
        self.chan_id = bot_id

    async def new_consumer(self,
                           callback: object = None,
                           size: int = 0,
                           priority_level: int = DEFAULT_PRIORITY_LEVEL,
                           subject: str = CHANNEL_WILDCARD,
                           action: str = CHANNEL_WILDCARD) -> OctoBotChannelConsumer:
        """
        Creates a new OctoBot Channel consumer
        :param callback: the consumer callback
        :param size: the consumer queue size
        :param priority_level: the consumer priority level
        :param subject: the consumer subject filtering
        :param action: the consumer action filtering
        :return: the consumer instance created
        """
        consumer = OctoBotChannelConsumer(callback, size=size, priority_level=priority_level)
        await self._add_new_consumer_and_run(consumer, subject=subject, action=action)
        return consumer

    def get_filtered_consumers(self, subject: str = CHANNEL_WILDCARD, action: str = CHANNEL_WILDCARD):
        """
        Returns the consumer that matches criteria
        :param subject: the subject criteria
        :param action: the action criteria
        :return: the matched consumers list
        """
        return self.get_consumer_from_filters({
            self.SUBJECT_KEY: subject,
            self.ACTION_KEY: action
        })

    async def _add_new_consumer_and_run(self, consumer, subject=CHANNEL_WILDCARD, action=CHANNEL_WILDCARD):
        """
        Add and run a created OctoBot channel consumer
        :param consumer: the consumer instance to run
        :param subject: the consumer subject filters
        :param action: the consumer action filters
        """
        consumer_filters: dict = {
            self.SUBJECT_KEY: subject,
            self.ACTION_KEY: action
        }

        self.add_new_consumer(consumer, consumer_filters)
        await consumer.run()
