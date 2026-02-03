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
import os

import pytest
import pytest_asyncio
import mock 

import async_channel.channels as channels
import async_channel.util as util
import async_channel

import tests


@pytest_asyncio.fixture
async def test_channel():
    channels.del_chan(tests.EMPTY_TEST_CHANNEL)
    yield await util.create_channel_instance(tests.EmptyTestChannel, channels.set_chan)
    await channels.get_chan(tests.EMPTY_TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_get_chan():
    class TestChannel(channels.Channel):
        pass

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    await channels.get_chan(tests.TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_set_chan():
    class TestChannel(channels.Channel):
        pass

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    with pytest.raises(ValueError):
        channels.set_chan(TestChannel(), name=TestChannel.get_name())
    await channels.get_chan(tests.TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_set_chan_using_default_name():
    class TestChannel(channels.Channel):
        pass

    channels.del_chan(tests.TEST_CHANNEL)
    channel = TestChannel()
    returned_channel = channels.set_chan(channel, name=None)
    assert returned_channel is channel
    assert channel.get_name() is not None
    assert channels.ChannelInstances.instance().channels[channel.get_name()] == channel
    with pytest.raises(ValueError):
        channels.set_chan(TestChannel(), name=TestChannel.get_name())
    await channels.get_chan(tests.TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_get_internal_producer():
    class TestChannel(channels.Channel):
        pass

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    with pytest.raises(TypeError):
        channels.get_chan(tests.TEST_CHANNEL).get_internal_producer()
    await channels.get_chan(tests.TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_new_consumer_without_producer(test_channel):
    await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    assert len(channels.get_chan(tests.EMPTY_TEST_CHANNEL).consumers) == 1


@pytest.mark.asyncio
async def test_new_consumer_without_filters(test_channel):
    consumer = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumers() == [consumer]


@pytest.mark.asyncio
async def test_new_consumer_with_filters(test_channel):
    consumer = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback, {"test_key": 1})
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumers() == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({}) == [consumer]  # returns all if empty
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 2}) == []
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 1, "test2": 2}) == []
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 1}) == [consumer]


@pytest.mark.asyncio
async def test_new_consumer_with_expected_wildcard_filters(test_channel):
    consumer = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback, {"test_key": 1,
                                                                                     "test_key_2": "abc"})
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumers() == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({}) == [consumer]  # returns all if empty
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 1, "test_key_2": "abc"}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": 1, "test_key_2": "abc", "test_key_3": 45}) == []
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": 1, "test_key_2": "abc", "test_key_3": async_channel.CHANNEL_WILDCARD}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 4, "test_key_2": "bc"}) == []
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 1, "test_key_2": async_channel.CHANNEL_WILDCARD}) == [
        consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 3, "test_key_2": async_channel.CHANNEL_WILDCARD}) == []
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": async_channel.CHANNEL_WILDCARD, "test_key_2": "abc"}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": async_channel.CHANNEL_WILDCARD, "test_key_2": "a"}) == []
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": async_channel.CHANNEL_WILDCARD, "test_key_2": async_channel.CHANNEL_WILDCARD}) == [consumer]


@pytest.mark.asyncio
async def test_new_consumer_with_consumer_wildcard_filters(test_channel):
    consumer = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback, {"test_key": 1,
                                                                                     "test_key_2": "abc",
                                                                                     "test_key_3": async_channel.CHANNEL_WILDCARD})
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumers() == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({}) == [consumer]  # returns all if empty
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 1, "test_key_2": "abc"}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": 1, "test_key_2": "abc", "test_key_3": 45}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": 1, "test_key_2": "abc", "test_key_3": async_channel.CHANNEL_WILDCARD}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 4, "test_key_2": "bc"}) == []
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 1, "test_key_2": async_channel.CHANNEL_WILDCARD}) == [
        consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 1}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key_2": async_channel.CHANNEL_WILDCARD}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key_3": async_channel.CHANNEL_WILDCARD}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key_3": "e"}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"test_key": 3, "test_key_2": async_channel.CHANNEL_WILDCARD}) == []
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": async_channel.CHANNEL_WILDCARD, "test_key_2": "abc"}) == [consumer]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": async_channel.CHANNEL_WILDCARD, "test_key_2": "a"}) == []
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": async_channel.CHANNEL_WILDCARD, "test_key_2": "a", "test_key_3": async_channel.CHANNEL_WILDCARD}) == []
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters(
        {"test_key": async_channel.CHANNEL_WILDCARD, "test_key_2": async_channel.CHANNEL_WILDCARD}) == [consumer]


@pytest.mark.asyncio
async def test_new_consumer_with_multiple_consumer_filtering(test_channel):
    consumers_descriptions = [
        {"A": 1, "B": 2, "C": async_channel.CHANNEL_WILDCARD},  # 0
        {"A": False, "B": "BBBB", "C": async_channel.CHANNEL_WILDCARD},  # 1
        {"A": 3, "B": async_channel.CHANNEL_WILDCARD, "C": async_channel.CHANNEL_WILDCARD},  # 2
        {"A": async_channel.CHANNEL_WILDCARD, "B": async_channel.CHANNEL_WILDCARD, "C": async_channel.CHANNEL_WILDCARD},  # 3
        {"A": async_channel.CHANNEL_WILDCARD, "B": 2, "C": 1},  # 4
        {"A": True, "B": async_channel.CHANNEL_WILDCARD, "C": async_channel.CHANNEL_WILDCARD},  # 5
        {"A": None, "B": None, "C": async_channel.CHANNEL_WILDCARD},  # 6
        {"A": "PPP", "B": 1, "C": async_channel.CHANNEL_WILDCARD, "D": 5},  # 7
        {"A": async_channel.CHANNEL_WILDCARD, "B": 2, "C": "ABC"},  # 8
        {"A": async_channel.CHANNEL_WILDCARD, "B": True, "C": async_channel.CHANNEL_WILDCARD},  # 9
        {"A": async_channel.CHANNEL_WILDCARD, "B": 6, "C": async_channel.CHANNEL_WILDCARD, "D": async_channel.CHANNEL_WILDCARD},  # 10
        {"A": async_channel.CHANNEL_WILDCARD, "B": async_channel.CHANNEL_WILDCARD, "C": async_channel.CHANNEL_WILDCARD, "D": async_channel.CHANNEL_WILDCARD},  # 11
        {"A": None, "B": False, "C": "LLLL", "D": async_channel.CHANNEL_WILDCARD},  # 12
        {"A": None, "B": None, "C": async_channel.CHANNEL_WILDCARD, "D": None},  # 13
        {"A": async_channel.CHANNEL_WILDCARD, "B": 2, "C": async_channel.CHANNEL_WILDCARD, "D": None},  # 14
        {"A": async_channel.CHANNEL_WILDCARD, "B": [2, 3, 4, 5, 6], "C": async_channel.CHANNEL_WILDCARD, "D": None},  # 15
        {"A": async_channel.CHANNEL_WILDCARD, "B": ["A", 5, "G"], "C": async_channel.CHANNEL_WILDCARD, "D": None},  # 16
        {"A": [1, 2, 3], "B": 2, "C": async_channel.CHANNEL_WILDCARD, "D": async_channel.CHANNEL_WILDCARD},  # 17
        {"A": ["A", "B", "C"], "B": 2, "C": async_channel.CHANNEL_WILDCARD, "D": async_channel.CHANNEL_WILDCARD},  # 18
        {"A": async_channel.CHANNEL_WILDCARD, "B": [2], "C": async_channel.CHANNEL_WILDCARD, "D": async_channel.CHANNEL_WILDCARD},  # 19
        {"A": async_channel.CHANNEL_WILDCARD, "B": ["B"], "C": async_channel.CHANNEL_WILDCARD, "D": async_channel.CHANNEL_WILDCARD},  # 20
        {"A": 18, "B": ["A", "B", "C"], "C": ["---", "9", "#"], "D": async_channel.CHANNEL_WILDCARD},  # 21
        {"A": [9, 18], "B": ["B", "C", "D"], "C": ["---", "9", "#", "@", "{"], "D": ["P", "__str__"]}  # 22
    ]

    consumers = [
        await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback, consumers_description)
        for consumers_description in consumers_descriptions
    ]

    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumers() == consumers
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({}) == consumers
    # Warning : consumer[5] is returned because 1 == True
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"A": 1, "B": "6"}) == \
           [consumers[3], consumers[5], consumers[11]]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"A": async_channel.CHANNEL_WILDCARD, "B": "G", "C": "1A"}) == \
           [consumers[2], consumers[3], consumers[5], consumers[11], consumers[16]]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"A": async_channel.CHANNEL_WILDCARD, "B": async_channel.CHANNEL_WILDCARD,
                                                                   "C": async_channel.CHANNEL_WILDCARD}) == consumers
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"A": 18, "B": "A", "C": "#"}) == \
           [consumers[3], consumers[11], consumers[16], consumers[21]]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"A": 18, "B": "C", "C": "#", "D": None}) == \
           [consumers[11], consumers[21]]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"A": 18, "B": "C", "C": "^", "D": None}) == \
           [consumers[11]]
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumer_from_filters({"A": 18, "B": "C", "C": "#", "D": "__str__"}) == \
           [consumers[11], consumers[21], consumers[22]]


@pytest.mark.asyncio
async def test_remove_consumer(test_channel):
    consumer = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumers() == [consumer]
    await channels.get_chan(tests.EMPTY_TEST_CHANNEL).remove_consumer(consumer)
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).get_consumers() == []


@pytest.mark.asyncio
async def test_unregister_producer(test_channel):
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).producers == []
    producer = tests.EmptyTestProducer(None)
    await channels.get_chan(tests.EMPTY_TEST_CHANNEL).register_producer(producer)
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).producers == [producer]


@pytest.mark.asyncio
async def test_register_producer(test_channel):
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).producers == []
    producer = tests.EmptyTestProducer(None)
    await channels.get_chan(tests.EMPTY_TEST_CHANNEL).register_producer(producer)
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).producers == [producer]
    channels.get_chan(tests.EMPTY_TEST_CHANNEL).unregister_producer(producer)
    assert channels.get_chan(tests.EMPTY_TEST_CHANNEL).producers == []


@pytest.mark.asyncio
async def test_flush(test_channel):
    producer = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer)
    producer2 = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer2)
    producer3 = tests.EmptyTestProducer(test_channel)
    test_channel.internal_producer = producer3

    assert producer3.channel is test_channel
    for producer in test_channel.producers:
        assert producer.channel is test_channel

    test_channel.flush()
    assert test_channel.internal_producer.channel is None
    for producer in test_channel.producers:
        assert producer.channel is None


@pytest.mark.asyncio
async def test_start(test_channel):
    consumer_1 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    consumer_2 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    with mock.patch.object(consumer_1, 'start', new=mock.AsyncMock()) as mocked_consumer_1_start:
        with mock.patch.object(consumer_2, 'start', new=mock.AsyncMock()) as mocked_consumer_2_start:
            await channels.get_chan(tests.EMPTY_TEST_CHANNEL).start()
            await tests.mock_was_called_once(mocked_consumer_1_start)
            await tests.mock_was_called_once(mocked_consumer_2_start)


@pytest.mark.asyncio
async def test_run(test_channel):
    consumer_1 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    consumer_2 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    with mock.patch.object(consumer_1, 'run', new=mock.AsyncMock()) as mocked_consumer_1_run:
        with mock.patch.object(consumer_2, 'run', new=mock.AsyncMock()) as mocked_consumer_2_run:
            await channels.get_chan(tests.EMPTY_TEST_CHANNEL).run()
            await tests.mock_was_called_once(mocked_consumer_1_run)
            await tests.mock_was_called_once(mocked_consumer_2_run)


@pytest.mark.asyncio
async def test_modify(test_channel):
    producer = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer)
    producer_2 = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer_2)
    with mock.patch.object(producer, 'modify', new=mock.AsyncMock()) as mocked_producer_1_modify:
        with mock.patch.object(producer_2, 'modify', new=mock.AsyncMock()) as mocked_producer_2_modify:
            await channels.get_chan(tests.EMPTY_TEST_CHANNEL).modify()
            await tests.mock_was_called_once(mocked_producer_1_modify)
            await tests.mock_was_called_once(mocked_producer_2_modify)


@pytest.mark.asyncio
async def test_should_pause_producers_with_no_consumers(test_channel):
    producer = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer)
    test_channel.is_paused = False
    if not os.getenv('CYTHON_IGNORE'):
        assert test_channel._should_pause_producers()


@pytest.mark.asyncio
async def test_should_pause_producers_when_already_paused(test_channel):
    producer = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer)
    test_channel.is_paused = True
    if not os.getenv('CYTHON_IGNORE'):
        assert not test_channel._should_pause_producers()


@pytest.mark.asyncio
async def test_should_pause_producers_with_priority_consumers(test_channel):
    producer = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer)
    consumer_1 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.HIGH.value)
    consumer_2 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.MEDIUM.value)
    consumer_3 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.OPTIONAL.value)
    test_channel.is_paused = False
    if not os.getenv('CYTHON_IGNORE'):
        assert not test_channel._should_pause_producers()
    await test_channel.remove_consumer(consumer_1)
    await test_channel.remove_consumer(consumer_2)
    await test_channel.remove_consumer(consumer_3)


@pytest.mark.asyncio
async def test_should_pause_producers_with_optional_consumers(test_channel):
    producer = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer)
    consumer_1 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.OPTIONAL.value)
    consumer_2 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.OPTIONAL.value)
    consumer_3 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.OPTIONAL.value)
    test_channel.is_paused = False
    if not os.getenv('CYTHON_IGNORE'):
        assert test_channel._should_pause_producers()
    await test_channel.remove_consumer(consumer_1)
    await test_channel.remove_consumer(consumer_2)
    await test_channel.remove_consumer(consumer_3)


@pytest.mark.asyncio
async def test_should_resume_producers_with_no_consumers(test_channel):
    producer = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer)
    test_channel.is_paused = True
    if not os.getenv('CYTHON_IGNORE'):
        assert not test_channel._should_resume_producers()


@pytest.mark.asyncio
async def test_should_resume_producers_when_already_resumed(test_channel):
    producer = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer)
    test_channel.is_paused = False
    if not os.getenv('CYTHON_IGNORE'):
        assert not test_channel._should_resume_producers()


@pytest.mark.asyncio
async def test_should_resume_producers_with_priority_consumers(test_channel):
    producer = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer)
    consumer_1 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.HIGH.value)
    consumer_2 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.MEDIUM.value)
    consumer_3 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.OPTIONAL.value)
    test_channel.is_paused = True
    if not os.getenv('CYTHON_IGNORE'):
        assert test_channel._should_resume_producers()
    await test_channel.remove_consumer(consumer_1)
    await test_channel.remove_consumer(consumer_2)
    await test_channel.remove_consumer(consumer_3)


@pytest.mark.asyncio
async def test_should_resume_producers_with_optional_consumers(test_channel):
    producer = tests.EmptyTestProducer(test_channel)
    await test_channel.register_producer(producer)
    consumer_1 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.OPTIONAL.value)
    consumer_2 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.OPTIONAL.value)
    consumer_3 = await channels.get_chan(tests.EMPTY_TEST_CHANNEL).new_consumer(
        tests.empty_test_callback,
        priority_level=async_channel.ChannelConsumerPriorityLevels.OPTIONAL.value)
    test_channel.is_paused = True
    if not os.getenv('CYTHON_IGNORE'):
        assert not test_channel._should_resume_producers()
    await test_channel.remove_consumer(consumer_1)
    await test_channel.remove_consumer(consumer_2)
    await test_channel.remove_consumer(consumer_3)
