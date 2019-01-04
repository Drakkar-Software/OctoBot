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

import pytest

from backtesting.backtesting_util import create_backtesting_config, create_backtesting_bot, start_backtesting_bot
from tests.test_utils.config import load_test_config


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_backtesting():
    config = create_backtesting_config(load_test_config(), ["ICX/BTC"])
    bot = create_backtesting_bot(config)
    previous_profitability, previous_market_profitability = await start_backtesting_bot(bot)
    config = create_backtesting_config(load_test_config(), ["ICX/BTC"])
    bot = create_backtesting_bot(config)
    current_profitability, current_market_profitability = await start_backtesting_bot(bot)

    # ensure no randomness in backtesting
    assert previous_profitability == current_profitability
    assert previous_market_profitability == current_market_profitability


async def test_multi_symbol_backtesting():
    config = create_backtesting_config(load_test_config(), ["ICX/BTC", "VEN/BTC", "XRB/BTC"])
    bot = create_backtesting_bot(config)
    previous_profitability, previous_market_profitability = await start_backtesting_bot(bot)
    bot = create_backtesting_bot(config)
    current_profitability, current_market_profitability = await start_backtesting_bot(bot)

    # ensure no randomness in backtesting
    assert previous_profitability == current_profitability
    assert previous_market_profitability == current_market_profitability
