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
import pytest_asyncio

from octobot_trading.exchange_data.exchange_symbols_data import ExchangeSymbolsData

# Import required fixtures
from tests import event_loop
from tests.exchanges import exchange_manager

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="function")
async def exchange_symbols_data(exchange_manager):
    return ExchangeSymbolsData(exchange_manager)


async def test_get_exchange_symbol_data(exchange_symbols_data):
    new_symbols_data = exchange_symbols_data.get_exchange_symbol_data("BTC/USDT")
    assert new_symbols_data is not None
    assert exchange_symbols_data.get_exchange_symbol_data("BTC/USDT") is new_symbols_data


async def test_get_exchange_symbol_data_without_creation(exchange_symbols_data):
    with pytest.raises(KeyError):
        exchange_symbols_data.get_exchange_symbol_data("BTC/USDT", allow_creation=False)
    exchange_symbols_data.get_exchange_symbol_data("ETH/USDT", allow_creation=True)
    with pytest.raises(KeyError):
        exchange_symbols_data.get_exchange_symbol_data("ETH/BTC", allow_creation=False)
