#  Drakkar-Software OctoBot-Trading
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

from octobot_commons.errors import ConfigTradingError

# Import required fixtures
from tests import event_loop, install_tentacles
from tests.exchanges import exchange_builder
from octobot_trading.api.exchange import cancel_ccxt_throttle_task

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures("event_loop", "exchange_builder")
async def test_create_without_trading_config(exchange_builder):
    with pytest.raises(ConfigTradingError):
        await exchange_builder.build()


@pytest.mark.usefixtures("event_loop", "exchange_builder")
async def test_create_without_installed_trading_mode(exchange_builder):
    with pytest.raises(ConfigTradingError):
        await exchange_builder.build()


@pytest.mark.usefixtures("event_loop", "exchange_builder", "install_tentacles")
async def test_create_without_installed_trading_mode(exchange_builder):
    with pytest.raises(ConfigTradingError):
        await exchange_builder.build()


@pytest.mark.usefixtures("event_loop", "exchange_builder", "install_tentacles")
async def test_create(exchange_builder):
    # await exchange_builder.build() # TODO
    pass


@pytest.mark.usefixtures("event_loop", "exchange_builder")
@pytest.mark.parametrize("exchange_builder", [(None, "binanceus")], indirect=["exchange_builder"])
async def test_create_basic(exchange_builder):
    exchange_builder.disable_trading_mode()
    exchange_manager = await exchange_builder.build()

    assert exchange_manager is not None
    assert exchange_manager.exchange_name == "binanceus"

    cancel_ccxt_throttle_task()
    await exchange_manager.stop()
