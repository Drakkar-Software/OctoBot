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

import async_channel.consumer as channel_consumer
import async_channel.channels as channels
import async_channel.producer as channel_producer
import async_channel.util as util
import tests 


@pytest.mark.asyncio
async def test_send_internal_producer_without_consumer():
    class TestProducer(channel_producer.Producer):
        async def send(self, data, **kwargs):
            await super().send(data)
            await channels.get_chan(tests.TEST_CHANNEL).stop()

        async def pause(self):
            pass

        async def resume(self):
            pass

    class TestChannel(channels.Channel):
        PRODUCER_CLASS = TestProducer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    await channels.get_chan(tests.TEST_CHANNEL).get_internal_producer().send({})


@pytest.mark.asyncio
async def test_send_producer_without_consumer():
    class TestProducer(channel_producer.Producer):
        async def send(self, data, **kwargs):
            await super().send(data)
            await channels.get_chan(tests.TEST_CHANNEL).stop()

        async def pause(self):
            pass

        async def resume(self):
            pass

    class TestConsumer(channel_consumer.Consumer):
        async def consume(self):
            while not self.should_stop:
                await self.callback(**(await self.queue.get()))

    class TestChannel(channels.Channel):
        PRODUCER_CLASS = TestProducer
        CONSUMER_CLASS = TestConsumer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)

    producer = TestProducer(channels.get_chan(tests.TEST_CHANNEL))
    await producer.run()
    await producer.send({})


@pytest.mark.asyncio
async def test_send_producer_with_consumer():
    class TestConsumer(channel_consumer.Consumer):
        pass

    class TestChannel(channels.Channel):
        PRODUCER_CLASS = tests.EmptyTestProducer
        CONSUMER_CLASS = TestConsumer

    async def callback(data):
        assert data == "test"
        await channels.get_chan(tests.TEST_CHANNEL).stop()

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    await channels.get_chan(tests.TEST_CHANNEL).new_consumer(callback)

    producer = tests.EmptyTestProducer(channels.get_chan(tests.TEST_CHANNEL))
    await producer.run()
    await producer.send({"data": "test"})


@pytest.mark.asyncio
async def test_pause_producer_without_consumers():
    class TestProducer(channel_producer.Producer):
        async def pause(self):
            await channels.get_chan(tests.TEST_CHANNEL).stop()

        async def pause(self):
            pass

        async def resume(self):
            pass

    class TestChannel(channels.Channel):
        PRODUCER_CLASS = TestProducer
        CONSUMER_CLASS = tests.EmptyTestConsumer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    await TestProducer(channels.get_chan(tests.TEST_CHANNEL)).run()


@pytest.mark.asyncio
async def test_pause_producer_with_removed_consumer():
    class TestProducer(channel_producer.Producer):
        async def pause(self):
            await channels.get_chan(tests.TEST_CHANNEL).stop()

        async def pause(self):
            pass

        async def resume(self):
            pass

    class TestChannel(channels.Channel):
        PRODUCER_CLASS = TestProducer
        CONSUMER_CLASS = tests.EmptyTestConsumer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    consumer = await channels.get_chan(tests.TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    await TestProducer(channels.get_chan(tests.TEST_CHANNEL)).run()
    await channels.get_chan(tests.TEST_CHANNEL).remove_consumer(consumer)


@pytest.mark.asyncio
async def test_resume_producer():
    class TestProducer(channel_producer.Producer):
        async def resume(self):
            await channels.get_chan(tests.TEST_CHANNEL).stop()

        async def pause(self):
            pass

        async def resume(self):
            pass

    class TestChannel(channels.Channel):
        PRODUCER_CLASS = TestProducer
        CONSUMER_CLASS = tests.EmptyTestConsumer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    await TestProducer(channels.get_chan(tests.TEST_CHANNEL)).run()
    await channels.get_chan(tests.TEST_CHANNEL).new_consumer(tests.empty_test_callback)


@pytest.mark.asyncio
async def test_resume_producer():
    class TestSupervisedConsumer(channel_consumer.SupervisedConsumer):
        pass

    class TestChannel(channels.Channel):
        PRODUCER_CLASS = tests.EmptyTestProducer
        CONSUMER_CLASS = TestSupervisedConsumer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    producer = tests.EmptyTestProducer(channels.get_chan(tests.TEST_CHANNEL))
    await producer.run()
    await channels.get_chan(tests.TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    await channels.get_chan(tests.TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    await channels.get_chan(tests.TEST_CHANNEL).new_consumer(tests.empty_test_callback)
    await producer.send({"data": "test"})
    await producer.wait_for_processing()
    await channels.get_chan(tests.TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_producer_is_running():
    class TestChannel(channels.Channel):
        PRODUCER_CLASS = tests.EmptyTestProducer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    producer = tests.EmptyTestProducer(channels.get_chan(tests.TEST_CHANNEL))
    assert not producer.is_running
    await producer.run()
    assert producer.is_running
    await channels.get_chan(tests.TEST_CHANNEL).stop()
    assert not producer.is_running


@pytest.mark.asyncio
async def test_producer_pause_resume():
    class TestChannel(channels.Channel):
        PRODUCER_CLASS = channel_producer.Producer

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    producer = channel_producer.Producer(channels.get_chan(tests.TEST_CHANNEL))
    assert producer.channel.is_paused
    await producer.pause()
    assert producer.channel.is_paused
    await producer.resume()
    assert not producer.channel.is_paused
    await producer.pause()
    assert producer.channel.is_paused
    await producer.resume()
    assert not producer.channel.is_paused
    await channels.get_chan(tests.TEST_CHANNEL).stop()
