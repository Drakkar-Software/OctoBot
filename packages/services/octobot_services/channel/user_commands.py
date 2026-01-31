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
import async_channel.channels as channels
import async_channel.producer as producer
import async_channel.consumer as consumer


class UserCommandsChannelConsumer(consumer.SupervisedConsumer):
    pass


class UserCommandsChannelProducer(producer.Producer):
    async def send(self, bot_id, subject, action, data=None):
        for consumer in self.channel.get_consumer_from_filters({"bot_id": bot_id, "subject": subject}):
            await consumer.queue.put({
                "bot_id": bot_id,
                "subject": subject,
                "action": action,
                "data": data
            })


class UserCommandsChannel(channels.Channel):
    PRODUCER_CLASS = UserCommandsChannelProducer
    CONSUMER_CLASS = UserCommandsChannelConsumer
