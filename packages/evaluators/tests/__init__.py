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
import asyncio
import pytest
import pytest_asyncio
import os.path as path
import aiohttp

import async_channel.util.channel_creator as channel_creator
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_evaluators.api as evaluator_api
import octobot_evaluators.evaluators.channel as evaluator_channels
import octobot_evaluators.matrix.channel as matrix_channels
import octobot_evaluators.matrix.matrices as matrices
import octobot_tentacles_manager.api as tentacles_api
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.managers as managers


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    # use ErrorContainer to catch otherwise hidden exceptions occurring in async scheduled tasks
    error_container = asyncio_tools.ErrorContainer()
    loop.set_exception_handler(error_container.exception_handler)
    yield loop
    # will fail if exceptions have been silently raised
    loop.run_until_complete(error_container.check())
    loop.close()


@pytest_asyncio.fixture
async def matrix_id():
    created_matrix_id = evaluator_api.create_matrix()
    yield created_matrix_id
    matrices.Matrices.instance().del_matrix(created_matrix_id)


@pytest_asyncio.fixture
async def install_tentacles():
    tentacles_folder_name = constants.TENTACLES_PATH
    def _cleanup(raises=True):
        if path.exists(tentacles_folder_name):
            managers.TentaclesSetupManager.delete_tentacles_arch(
                force=True, raises=raises, tentacles_folder_name=tentacles_folder_name
            )

    def _tentacles_local_path():
        return path.join("tests", "static", "tentacles.zip")

    _cleanup(False)
    async with aiohttp.ClientSession() as session:
        if nb_errors := await tentacles_api.install_all_tentacles(
            _tentacles_local_path(), tentacle_path=tentacles_folder_name, aiohttp_session=session
        ):
            raise AssertionError(f"Failed to install tentacles: {nb_errors} error(s) occurred")
        yield 
        import tentacles
    _cleanup()


@pytest_asyncio.fixture
async def evaluators_and_matrix_channels(matrix_id):
    evaluators_channel = await channel_creator.create_channel_instance(evaluator_channels.EvaluatorsChannel,
                                                                       evaluator_channels.set_chan,
                                                                       matrix_id=matrix_id)
    matrix_channel = await channel_creator.create_channel_instance(matrix_channels.MatrixChannel,
                                                                   evaluator_channels.set_chan,
                                                                   matrix_id=matrix_id)
    yield matrix_id
    await evaluators_channel.stop()
    await matrix_channel.stop()
    evaluator_api.del_evaluator_channels(matrix_id)
