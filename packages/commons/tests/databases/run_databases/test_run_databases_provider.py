#  Drakkar-Software OctoBot
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
import mock
import pytest
import pytest_asyncio
import octobot_commons.databases as databases


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def run_database_identifier():
    return mock.Mock(
        initialize=mock.AsyncMock(),
        close=mock.AsyncMock()
    )


@pytest.fixture
def run_database_provider():
    return databases.RunDatabasesProvider.instance()


async def test_add_bot_id(run_database_provider, run_database_identifier):
    await run_database_provider.add_bot_id("123", run_database_identifier)
    run_database_provider.get_run_databases_identifier("123").initialize.assert_called_once()
    assert "123" in run_database_provider.run_databases


async def test_has_bot_id(run_database_provider, run_database_identifier):
    await run_database_provider.add_bot_id("123", run_database_identifier)
    assert run_database_provider.has_bot_id("123") is True
    assert run_database_provider.has_bot_id("1232") is False


async def test_close(run_database_provider, run_database_identifier):
    await run_database_provider.add_bot_id("123", run_database_identifier)
    await run_database_provider.close("123")
    with pytest.raises(KeyError):
        await run_database_provider.close("aa")
