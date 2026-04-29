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

import pytest
import pytest_asyncio
import mock 

import async_channel.consumer as channel_consumer
import async_channel.channels as channels
import async_channel.util as util
import tests 


async def init_consumer_test():
    class TestChannel(channels.Channel):
        PRODUCER_CLASS = tests.EmptyTestProducer
        CONSUMER_CLASS = tests.EmptyTestConsumer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    producer = tests.EmptyTestProducer(channels.get_chan(tests.TEST_CHANNEL))
    await producer.run()
    return await channels.get_chan(tests.TEST_CHANNEL).new_consumer(tests.empty_test_callback)


@pytest.mark.asyncio
async def test_perform_called():
    consumer = await init_consumer_test()
    with mock.patch.object(consumer, 'perform', new=mock.AsyncMock()) as mocked_consume_ends:
        await channels.get_chan(tests.TEST_CHANNEL).get_internal_producer().send({})
        await tests.mock_was_called_once(mocked_consume_ends)

    await channels.get_chan(tests.TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_consume_ends_called():
    consumer = await init_consumer_test()
    with mock.patch.object(consumer, 'consume_ends', new=mock.AsyncMock()) as mocked_consume_ends:
        await channels.get_chan(tests.TEST_CHANNEL).get_internal_producer().send({})
        await tests.mock_was_called_once(mocked_consume_ends)

    await channels.get_chan(tests.TEST_CHANNEL).stop()


@pytest_asyncio.fixture
async def internal_consumer():
    class TestInternalConsumer(channel_consumer.InternalConsumer):
        async def perform(self, kwargs):
            pass

    class TestChannel(channels.Channel):
        PRODUCER_CLASS = tests.EmptyTestProducer
        CONSUMER_CLASS = TestInternalConsumer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    producer = tests.EmptyTestProducer(channels.get_chan(tests.TEST_CHANNEL))
    await producer.run()
    yield TestInternalConsumer()
    await channels.get_chan(tests.TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_internal_consumer(internal_consumer):
    await channels.get_chan(tests.TEST_CHANNEL).new_consumer(internal_consumer=internal_consumer)

    with mock.patch.object(internal_consumer, 'perform', new=mock.AsyncMock()) as mocked_consume_ends:
        await channels.get_chan(tests.TEST_CHANNEL).get_internal_producer().send({})
        await tests.mock_was_called_once(mocked_consume_ends)


@pytest.mark.asyncio
async def test_default_internal_consumer_callback(internal_consumer):
    with pytest.raises(NotImplementedError):
        await internal_consumer.internal_callback()


@pytest.mark.asyncio
async def test_supervised_consumer():
    class TestSupervisedConsumer(channel_consumer.SupervisedConsumer):
        pass

    class TestChannel(channels.Channel):
        PRODUCER_CLASS = tests.EmptyTestProducer
        CONSUMER_CLASS = TestSupervisedConsumer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    producer = tests.EmptyTestProducer(channels.get_chan(tests.TEST_CHANNEL))
    await producer.run()
    consumer = await channels.get_chan(tests.TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    await channels.get_chan(tests.TEST_CHANNEL).get_internal_producer().send({})
    await consumer.queue.join()
    await channels.get_chan(tests.TEST_CHANNEL).stop()
