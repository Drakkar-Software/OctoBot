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
import uuid

import pytest
import pytest_asyncio

import async_channel.channels as channels
import async_channel.util as util
import tests


@pytest_asyncio.fixture
async def chan_id():
    channel_uuid = uuid.uuid4().hex
    await util.create_channel_instance(tests.EmptyTestWithIdChannel, channels.set_chan_at_id, test_id=channel_uuid)
    return channel_uuid


@pytest_asyncio.fixture
async def channel_id():
    channel_uuid = uuid.uuid4().hex
    await util.create_channel_instance(tests.EmptyTestWithIdChannel, channels.set_chan_at_id, test_id=channel_uuid)
    yield channel_uuid
    await channels.get_chan_at_id(tests.EMPTY_TEST_WITH_ID_CHANNEL, channel_uuid).stop()
    channels.del_chan_at_id(tests.EMPTY_TEST_WITH_ID_CHANNEL, channel_uuid)


@pytest.mark.asyncio
async def test_get_chan_at_id(channel_id):
    assert channels.get_chan_at_id(tests.EMPTY_TEST_WITH_ID_CHANNEL, channel_id)


@pytest.mark.asyncio
async def test_set_chan_at_id_already_exist(channel_id):
    with pytest.raises(ValueError):
        await util.create_channel_instance(tests.EmptyTestWithIdChannel, channels.set_chan_at_id, test_id=channel_id)


@pytest.mark.asyncio
async def test_del_channel_container_not_exist_does_not_raise(channel_id):
    channels.del_channel_container(channel_id + "test")


@pytest.mark.asyncio
async def test_del_channel_container(chan_id):
    channels.del_channel_container(chan_id)
    with pytest.raises(KeyError):
        channels.get_chan_at_id(tests.EMPTY_TEST_WITH_ID_CHANNEL, chan_id)
    channels.del_chan_at_id(tests.EMPTY_TEST_WITH_ID_CHANNEL, chan_id)


@pytest.mark.asyncio
async def test_get_channels_not_exist(channel_id):
    with pytest.raises(KeyError):
        channels.get_channels(channel_id + "test")


@pytest.mark.asyncio
async def test_get_channels(chan_id):
    class EmptyTestWithId2Channel(tests.EmptyTestWithIdChannel):
        pass

    class EmptyTestWithId3Channel(tests.EmptyTestWithIdChannel):
        pass

    class EmptyTestWithId4Channel(tests.EmptyTestWithIdChannel):
        pass

    class EmptyTestWithId5Channel(tests.EmptyTestWithIdChannel):
        pass

    class EmptyTestWithId6Channel(tests.EmptyTestWithIdChannel):
        pass

    channel_4_id = uuid.uuid4().hex
    channel_6_id = uuid.uuid4().hex
    ch1 = channels.get_chan_at_id(tests.EMPTY_TEST_WITH_ID_CHANNEL, chan_id)
    ch2 = await util.create_channel_instance(EmptyTestWithId2Channel, channels.set_chan_at_id, test_id=chan_id)
    ch3 = await util.create_channel_instance(EmptyTestWithId3Channel, channels.set_chan_at_id, test_id=chan_id)
    ch4 = await util.create_channel_instance(EmptyTestWithId4Channel, channels.set_chan_at_id, test_id=channel_4_id)
    ch5 = await util.create_channel_instance(EmptyTestWithId5Channel, channels.set_chan_at_id, test_id=channel_4_id)
    ch6 = await util.create_channel_instance(EmptyTestWithId6Channel, channels.set_chan_at_id, test_id=channel_6_id)
    assert len(channels.get_channels(chan_id)) == 3
    assert len(channels.get_channels(channel_4_id)) == 2
    assert len(channels.get_channels(channel_6_id)) == 1
    assert channels.get_channels(chan_id) == {
        "EmptyTestWithId": ch1,
        "EmptyTestWithId2": ch2,
        "EmptyTestWithId3": ch3
    }
    assert channels.get_channels(channel_4_id) == {
        "EmptyTestWithId4": ch4,
        "EmptyTestWithId5": ch5
    }
    assert channels.get_channels(channel_6_id) == {
        "EmptyTestWithId6": ch6
    }
    channels.del_channel_container(chan_id)
    channels.del_channel_container(channel_4_id)
    channels.del_channel_container(channel_6_id)
