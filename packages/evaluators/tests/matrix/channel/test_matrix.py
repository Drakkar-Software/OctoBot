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

from octobot_evaluators.api.evaluators import create_matrix
from octobot_evaluators.api.initialization import create_evaluator_channels, del_evaluator_channels
from octobot_evaluators.evaluators.channel.evaluator_channel import get_chan
from octobot_evaluators.constants import MATRIX_CHANNEL
from octobot_evaluators.matrix.matrix_manager import get_tentacle_path
from octobot_evaluators.matrix.matrices import Matrices

MATRIX_TEST_ID = "test"


async def matrix_callback(matrix_id,
                          evaluator_name,
                          evaluator_type,
                          eval_note,
                          eval_note_type,
                          eval_note_description,
                          eval_note_metadata,
                          exchange_name,
                          cryptocurrency,
                          symbol,
                          time_frame):
    pass


@pytest.mark.asyncio
async def test_evaluator_channel_creation():
    del_evaluator_channels(MATRIX_TEST_ID)
    await create_evaluator_channels(MATRIX_TEST_ID)
    await get_chan(MATRIX_CHANNEL, MATRIX_TEST_ID).new_consumer(matrix_callback)
    await get_chan(MATRIX_CHANNEL, MATRIX_TEST_ID).stop()


@pytest.mark.asyncio
async def test_evaluator_channel_send():
    del_evaluator_channels(MATRIX_TEST_ID)
    matrix_id = create_matrix()
    await create_evaluator_channels(MATRIX_TEST_ID)
    await get_chan(MATRIX_CHANNEL, MATRIX_TEST_ID).new_consumer(matrix_callback)
    await get_chan(MATRIX_CHANNEL, MATRIX_TEST_ID).get_internal_producer().send(matrix_id=matrix_id,
                                                                                evaluator_name="test",
                                                                                evaluator_type="test2",
                                                                                eval_note=1)

    # following assert should be None because send() doesn't call set_tentacle_value
    assert Matrices.instance().get_matrix(matrix_id).get_node_at_path(
        get_tentacle_path(tentacle_name="test", tentacle_type="test2")) is None
    await get_chan(MATRIX_CHANNEL, MATRIX_TEST_ID).stop()
    Matrices.instance().del_matrix(matrix_id)


@pytest.mark.asyncio
async def test_evaluator_channel_send_eval_note():
    del_evaluator_channels(MATRIX_TEST_ID)
    matrix_id = create_matrix()
    await create_evaluator_channels(MATRIX_TEST_ID)
    await get_chan(MATRIX_CHANNEL, MATRIX_TEST_ID).new_consumer(matrix_callback)
    await get_chan(MATRIX_CHANNEL, MATRIX_TEST_ID).get_internal_producer().send_eval_note(matrix_id=matrix_id,
                                                                                          evaluator_name="test",
                                                                                          evaluator_type="test2",
                                                                                          eval_note=1,
                                                                                          eval_note_type=int,
                                                                                          eval_note_description="test description",
                                                                                          eval_time=1000,
                                                                                          eval_note_metadata={"test": "test"})

    assert Matrices.instance().get_matrix(matrix_id).get_node_at_path(
        get_tentacle_path(tentacle_name="test", tentacle_type="test2")).node_value == 1
    assert Matrices.instance().get_matrix(matrix_id).get_node_at_path(
        get_tentacle_path(tentacle_name="test", tentacle_type="test2")).node_description == "test description"
    assert Matrices.instance().get_matrix(matrix_id).get_node_at_path(
        get_tentacle_path(tentacle_name="test", tentacle_type="test2")).node_metadata == {"test": "test"}
    assert Matrices.instance().get_matrix(matrix_id).get_node_at_path(
        get_tentacle_path(tentacle_name="test", tentacle_type="test2")).node_value_time == 1000
    await get_chan(MATRIX_CHANNEL, MATRIX_TEST_ID).stop()
    Matrices.instance().del_matrix(matrix_id)
