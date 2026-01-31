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

from octobot_commons.tests.test_config import load_test_config

from octobot_trading.api.exchange import create_exchange_builder, \
    get_exchange_configurations_from_exchange_name, get_exchange_manager_from_exchange_name_and_id
from octobot_trading.exchanges.exchanges import Exchanges
from tests.exchanges import exchange_manager
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_create_exchange_builder():
    exchange_builder = create_exchange_builder(load_test_config(), "binanceus")
    assert exchange_builder


async def test_get_exchange_configurations_from_exchange_name(exchange_manager):
    Exchanges.instance().add_exchange(exchange_manager, None)
    assert get_exchange_configurations_from_exchange_name("binanceus")
    with pytest.raises(KeyError):
        get_exchange_configurations_from_exchange_name("bybit")


async def test_get_exchange_manager_from_exchange_name_and_id(exchange_manager):
    Exchanges.instance().add_exchange(exchange_manager, None)
    assert get_exchange_manager_from_exchange_name_and_id(exchange_manager.exchange_name, exchange_manager.id)
    with pytest.raises(KeyError):
        get_exchange_manager_from_exchange_name_and_id(exchange_manager.exchange_name, "test")
    with pytest.raises(KeyError):
        get_exchange_manager_from_exchange_name_and_id("bybit", exchange_manager.id)
