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
import pytest_asyncio

import mock
import pytest

import async_channel.channels as channels
import async_channel.producer as channel_producer
import async_channel.util as util
import tests 

TEST_SYNCHRONIZED_CHANNEL = "SynchronizedTest"


class SynchronizedProducerTest(channel_producer.Producer):
    async def send(self, data, **kwargs):
        await super().send(data)
        await channels.get_chan(TEST_SYNCHRONIZED_CHANNEL).stop()

    async def pause(self):
        pass

    async def resume(self):
        pass


class SynchronizedChannelTest(channels.Channel):
    PRODUCER_CLASS = SynchronizedProducerTest
    CONSUMER_CLASS = tests.EmptyTestConsumer


@pytest_asyncio.fixture
async def synchronized_channel():
    yield await util.create_channel_instance(SynchronizedChannelTest, channels.set_chan, is_synchronized=True)
    channels.del_chan(TEST_SYNCHRONIZED_CHANNEL)


@pytest.mark.asyncio
async def test_producer_synchronized_perform_consumers_queue_with_one_consumer(synchronized_channel):
    async def callback():
        pass

    test_consumer = await synchronized_channel.new_consumer(callback)

    producer = SynchronizedProducerTest(channels.get_chan(TEST_SYNCHRONIZED_CHANNEL))
    await producer.run()

    with mock.patch.object(test_consumer, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_callback:
        await producer.send({})
        await tests.mock_was_not_called(mocked_test_consumer_callback)
        await producer.synchronized_perform_consumers_queue(1, True, 1)
        await tests.mock_was_called_once(mocked_test_consumer_callback)


@pytest.mark.asyncio
async def test_producer_synchronized_perform_supervised_consumer_with_processing_empty_queue(synchronized_channel):
    continue_event = asyncio.Event()
    calls = []
    done_calls = []

    async def callback():
        calls.append(None)
        await asyncio.wait_for(continue_event.wait(), 1)
        done_calls.append(None)

    async def set_event_task():
        continue_event.set()

    # use supervised consumers
    synchronized_channel.CONSUMER_CLASS = tests.EmptyTestSupervisedConsumer
    test_consumer = await synchronized_channel.new_consumer(callback)

    producer = SynchronizedProducerTest(channels.get_chan(TEST_SYNCHRONIZED_CHANNEL))
    await producer.run()

    await producer.send({})
    await test_consumer.run()
    try:
        await tests.wait_asyncio_next_cycle()
        # called already yet
        assert calls == [None]
        # call not finished
        assert done_calls == []
        # queue is empty
        assert test_consumer.queue.qsize() == 0
        asyncio.create_task(set_event_task())
        # wait for call to finish even though queue is empty => does not work as we are not joining the
        # current processing
        await producer.synchronized_perform_consumers_queue(1, False, 1)
        assert done_calls == []
        # wait for call to finish even though queue is empty with join
        await producer.synchronized_perform_consumers_queue(1, True, 1)
        # ensure call actually finished (if we did not join the current task, this call would not have finished)
        assert done_calls == [None]
    finally:
        await test_consumer.stop()


@pytest.mark.asyncio
async def test_join():
    # just test this does not throw an error on base consumers
    base_consumer = tests.EmptyTestConsumer(None)
    await base_consumer.join(1)

    supervised_consumer = tests.EmptyTestSupervisedConsumer(None)
    assert supervised_consumer.idle.is_set()

    with mock.patch.object(supervised_consumer.idle, "wait", mock.AsyncMock()) as wait_mock:
        await supervised_consumer.join(1)
        wait_mock.assert_not_called()

        supervised_consumer.idle.clear()
        await supervised_consumer.join(1)
        wait_mock.assert_called_once()


@pytest.mark.asyncio
async def test_join_queue():
    base_consumer = tests.EmptyTestConsumer(None)
    with mock.patch.object(base_consumer.queue, "join", mock.AsyncMock()) as join_mock:
        await base_consumer.join_queue()
        join_mock.assert_not_called()

    supervised_consumer = tests.EmptyTestSupervisedConsumer(None)
    with mock.patch.object(supervised_consumer.queue, "join", mock.AsyncMock()) as join_mock:
        await supervised_consumer.join_queue()
        join_mock.assert_called_once()


@pytest.mark.asyncio
async def test_synchronized_no_tasks(synchronized_channel):
    async def callback():
        pass

    test_consumer = await synchronized_channel.new_consumer(callback)

    producer = SynchronizedProducerTest(channels.get_chan(TEST_SYNCHRONIZED_CHANNEL))
    await producer.run()

    assert test_consumer.consume_task is None
    assert producer.produce_task is None


@pytest.mark.asyncio
async def test_is_consumers_queue_empty_with_one_consumer(synchronized_channel):
    async def callback():
        pass

    await synchronized_channel.new_consumer(callback)

    producer = SynchronizedProducerTest(channels.get_chan(TEST_SYNCHRONIZED_CHANNEL))
    await producer.run()

    await producer.send({})
    assert not producer.is_consumers_queue_empty(1)
    assert not producer.is_consumers_queue_empty(2)
    await producer.synchronized_perform_consumers_queue(1, True, 1)
    assert producer.is_consumers_queue_empty(1)
    assert producer.is_consumers_queue_empty(2)


@pytest.mark.asyncio
async def test_is_consumers_queue_empty_with_multiple_consumers(synchronized_channel):
    async def callback():
        pass

    await synchronized_channel.new_consumer(callback)
    await synchronized_channel.new_consumer(callback)
    await synchronized_channel.new_consumer(callback, priority_level=2)
    await synchronized_channel.new_consumer(callback, priority_level=2)
    await synchronized_channel.new_consumer(callback, priority_level=3)

    producer = SynchronizedProducerTest(channels.get_chan(TEST_SYNCHRONIZED_CHANNEL))
    await producer.run()

    await producer.send({})
    assert not producer.is_consumers_queue_empty(1)
    assert not producer.is_consumers_queue_empty(2)
    assert not producer.is_consumers_queue_empty(3)
    await producer.synchronized_perform_consumers_queue(1, True, 1)
    assert producer.is_consumers_queue_empty(1)
    assert not producer.is_consumers_queue_empty(2)
    assert not producer.is_consumers_queue_empty(3)
    await producer.synchronized_perform_consumers_queue(2, True, 1)
    assert producer.is_consumers_queue_empty(1)
    assert producer.is_consumers_queue_empty(2)
    assert not producer.is_consumers_queue_empty(3)
    await producer.synchronized_perform_consumers_queue(2, True, 1)
    assert not producer.is_consumers_queue_empty(3)
    await producer.synchronized_perform_consumers_queue(3, True, 1)
    assert producer.is_consumers_queue_empty(3)


@pytest.mark.asyncio
async def test_producer_synchronized_perform_consumers_queue_with_multiple_consumer(synchronized_channel):
    async def callback():
        pass

    test_consumer_1_1 = await synchronized_channel.new_consumer(callback)
    test_consumer_1_2 = await synchronized_channel.new_consumer(callback)
    test_consumer_2_1 = await synchronized_channel.new_consumer(callback, priority_level=2)
    test_consumer_2_2 = await synchronized_channel.new_consumer(callback, priority_level=2)
    test_consumer_3_1 = await synchronized_channel.new_consumer(callback, priority_level=3)

    producer = SynchronizedProducerTest(channels.get_chan(TEST_SYNCHRONIZED_CHANNEL))
    await producer.run()

    with mock.patch.object(test_consumer_1_1, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_1_1_callback, \
            mock.patch.object(test_consumer_1_2, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_1_2_callback, \
            mock.patch.object(test_consumer_2_1, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_2_1_callback, \
            mock.patch.object(test_consumer_2_2, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_2_2_callback, \
            mock.patch.object(test_consumer_3_1, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_3_1_callback:
        await producer.send({})
        await tests.mock_was_not_called(mocked_test_consumer_1_1_callback)
        await tests.mock_was_not_called(mocked_test_consumer_1_2_callback)
        await tests.mock_was_not_called(mocked_test_consumer_2_1_callback)
        await tests.mock_was_not_called(mocked_test_consumer_2_2_callback)
        await tests.mock_was_not_called(mocked_test_consumer_3_1_callback)
        await producer.synchronized_perform_consumers_queue(1, True, 1)
        await tests.mock_was_called_once(mocked_test_consumer_1_1_callback)
        await tests.mock_was_called_once(mocked_test_consumer_1_2_callback)
        await tests.mock_was_not_called(mocked_test_consumer_2_1_callback)
        await tests.mock_was_not_called(mocked_test_consumer_2_2_callback)
        await tests.mock_was_not_called(mocked_test_consumer_3_1_callback)
        await producer.synchronized_perform_consumers_queue(2, True, 1)
        await tests.mock_was_called_once(mocked_test_consumer_1_1_callback)
        await tests.mock_was_called_once(mocked_test_consumer_1_2_callback)
        await tests.mock_was_called_once(mocked_test_consumer_2_1_callback)
        await tests.mock_was_called_once(mocked_test_consumer_2_2_callback)
        await tests.mock_was_not_called(mocked_test_consumer_3_1_callback)
        assert not producer.is_consumers_queue_empty(3)
        await producer.synchronized_perform_consumers_queue(3, True, 1)
        await tests.mock_was_called_once(mocked_test_consumer_3_1_callback)
        assert producer.is_consumers_queue_empty(1)
        assert producer.is_consumers_queue_empty(2)
        assert producer.is_consumers_queue_empty(3)

    with mock.patch.object(test_consumer_1_1, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_1_1_callback, \
            mock.patch.object(test_consumer_1_2, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_1_2_callback, \
            mock.patch.object(test_consumer_2_1, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_2_1_callback, \
            mock.patch.object(test_consumer_2_2, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_2_2_callback, \
            mock.patch.object(test_consumer_3_1, 'callback', new=mock.AsyncMock()) as mocked_test_consumer_3_1_callback:
        await producer.send({})
        await tests.mock_was_not_called(mocked_test_consumer_1_1_callback)
        await tests.mock_was_not_called(mocked_test_consumer_1_2_callback)
        await tests.mock_was_not_called(mocked_test_consumer_2_1_callback)
        await tests.mock_was_not_called(mocked_test_consumer_2_2_callback)
        await tests.mock_was_not_called(mocked_test_consumer_3_1_callback)
        assert not producer.is_consumers_queue_empty(2)
        await producer.synchronized_perform_consumers_queue(3, True, 1)
        await tests.mock_was_called_once(mocked_test_consumer_1_1_callback)
        await tests.mock_was_called_once(mocked_test_consumer_1_2_callback)
        await tests.mock_was_called_once(mocked_test_consumer_2_1_callback)
        await tests.mock_was_called_once(mocked_test_consumer_2_2_callback)
        await tests.mock_was_called_once(mocked_test_consumer_3_1_callback)
        assert producer.is_consumers_queue_empty(1)
        assert producer.is_consumers_queue_empty(2)
        assert producer.is_consumers_queue_empty(3)
