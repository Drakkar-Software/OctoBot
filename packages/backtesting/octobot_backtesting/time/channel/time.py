#  Drakkar-Software OctoBot-Backtesting
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

import async_channel.channels as channels
import async_channel.consumer as consumers
import async_channel.producer as producers


class TimeProducer(producers.Producer):
    def __init__(self, channel, backtesting):
        super().__init__(channel)
        self.backtesting = backtesting

    async def push(self, timestamp):
        await self.perform(timestamp)

    async def perform(self, timestamp):
        try:
            await self.backtesting.handle_time_update(timestamp)
            await self.send(timestamp)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering time update: {e}")

    async def send(self, timestamp, **kwargs):
        for consumer in self.channel.get_consumer_from_filters({}):
            await consumer.queue.put({
                "timestamp": timestamp
            })


class TimeConsumer(consumers.SupervisedConsumer):
    pass


class TimeChannel(channels.Channel):
    PRODUCER_CLASS = TimeProducer
    CONSUMER_CLASS = TimeConsumer

    @classmethod
    def get_name(cls, identifier=None) -> str:
        """
        Override of the default implementation to avoid naming conflicts
        :returns the channel name
        """
        if identifier is None:
            raise NotImplementedError("Provide identifier param or use backtesting.get_time_chan_name() instead")
        return f"{channels.Channel.get_name()}#{identifier}"

