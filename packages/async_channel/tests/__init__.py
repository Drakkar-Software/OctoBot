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
import asyncio

import async_channel.channels as channels
import async_channel.consumer as channel_consumer
import async_channel.producer as producer

TEST_CHANNEL = "Test"
EMPTY_TEST_CHANNEL = "EmptyTest"
EMPTY_TEST_WITH_ID_CHANNEL = "EmptyTestWithId"
CONSUMER_KEY = "test"


class EmptyTestConsumer(channel_consumer.Consumer):
    pass


class EmptyTestSupervisedConsumer(channel_consumer.SupervisedConsumer):
    pass


class EmptyTestProducer(producer.Producer):
    async def start(self):
        await asyncio.sleep(100000)

    async def pause(self):
        pass

    async def resume(self):
        pass


class EmptyTestChannel(channels.Channel):
    CONSUMER_CLASS = EmptyTestConsumer
    PRODUCER_CLASS = EmptyTestProducer


async def empty_test_callback():
    pass


async def mock_was_called_once(mocked_method):
    await wait_asyncio_next_cycle()
    mocked_method.assert_called_once()


async def mock_was_not_called(mocked_method):
    await wait_asyncio_next_cycle()
    mocked_method.assert_not_called()


class EmptyTestWithIdChannel(channels.Channel):
    CONSUMER_CLASS = EmptyTestConsumer
    PRODUCER_CLASS = EmptyTestProducer

    def __init__(self, test_id):
        super().__init__()
        self.chan_id = test_id


async def wait_asyncio_next_cycle():
    async def do_nothing():
        pass
    await asyncio.create_task(do_nothing())
