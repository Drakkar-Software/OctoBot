#  Drakkar-Software OctoBot-Evaluators
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

from async_channel.util.channel_creator import create_channel_instance
from octobot_evaluators.api.initialization import del_evaluator_channels
from octobot_evaluators.evaluators.channel.evaluator_channel import get_chan, set_chan, EvaluatorChannel
import octobot_commons.asyncio_tools as asyncio_tools

from tests import matrix_id

EVALUATOR_CHANNEL_NAME = "Evaluator"


async def evaluator_callback():
    pass


@pytest_asyncio.fixture
async def evaluator_channel(matrix_id):
    channel = None
    try:
        del_evaluator_channels(matrix_id)
        channel = await create_channel_instance(EvaluatorChannel, set_chan, matrix_id=matrix_id)
        yield matrix_id
    finally:
        if channel is not None:
            # gracefully stop channel
            await channel.stop()
        del_evaluator_channels(matrix_id)


@pytest.mark.asyncio
async def test_evaluator_channel_get_consumer_from_filters(evaluator_channel):
    consumer_1 = await get_chan(EVALUATOR_CHANNEL_NAME, evaluator_channel).new_consumer(evaluator_callback)
    consumer_2 = await get_chan(EVALUATOR_CHANNEL_NAME, evaluator_channel).new_consumer(evaluator_callback)
    consumer_3 = await get_chan(EVALUATOR_CHANNEL_NAME, evaluator_channel).new_consumer(evaluator_callback)
    assert get_chan(EVALUATOR_CHANNEL_NAME, evaluator_channel) \
               .get_consumer_from_filters({}) == [consumer_1, consumer_2, consumer_3]
    assert get_chan(EVALUATOR_CHANNEL_NAME, evaluator_channel) \
               .get_consumer_from_filters({}, origin_consumer=consumer_2) == [consumer_1, consumer_3]
    assert get_chan(EVALUATOR_CHANNEL_NAME, evaluator_channel) \
               .get_consumer_from_filters({}, origin_consumer=consumer_1) == [consumer_2, consumer_3]
    assert get_chan(EVALUATOR_CHANNEL_NAME, evaluator_channel) \
               .get_consumer_from_filters({}, origin_consumer=consumer_3) == [consumer_1, consumer_2]
