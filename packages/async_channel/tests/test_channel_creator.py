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
import copy 
import mock
import pytest

import async_channel.channels as channels
import async_channel.util as util

import tests 


@pytest.mark.asyncio
async def test_create_channel_instance():
    class TestChannel(channels.Channel):
        pass

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan)
    await channels.get_chan(tests.TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_create_synchronized_channel_instance():
    class TestChannel(channels.Channel):
        pass

    channels.del_chan(tests.TEST_CHANNEL)
    await util.create_channel_instance(TestChannel, channels.set_chan, is_synchronized=True)
    assert channels.get_chan(tests.TEST_CHANNEL).is_synchronized
    await channels.get_chan(tests.TEST_CHANNEL).stop()


@pytest.mark.asyncio
async def test_create_all_subclasses_channel():
    class TestChannelClass(channels.Channel):
        pass

    class Test1Channel(TestChannelClass):
        pass

    class Test2Channel(TestChannelClass):
        pass

    def clean_channels():
        for channel in copy.deepcopy(channels.ChannelInstances.instance().channels):
            channels.del_chan(channel)

    channels.del_chan(tests.TEST_CHANNEL)
    with mock.patch.object(
        TestChannelClass, '__subclasses__', mock.Mock(return_value=[Test1Channel, Test2Channel])
    ) as mock_subclasses:
        clean_channels()
        await util.create_all_subclasses_channel(TestChannelClass, channels.set_chan)
        assert sorted(channels.ChannelInstances.instance().channels) == sorted([
            chan.get_name() for chan in [Test1Channel, Test2Channel]
        ])
        mock_subclasses.assert_called_once()
        mock_subclasses.reset_mock()
        clean_channels()
        await util.create_all_subclasses_channel(TestChannelClass, channels.set_chan, is_synchronized=True)
        sync_channels = channels.ChannelInstances.instance().channels
        assert len(sync_channels) == 2
        assert all(channels.get_chan(channel).is_synchronized for channel in sync_channels)
        clean_channels()
        mock_subclasses.assert_called_once()
        mock_subclasses.reset_mock()
