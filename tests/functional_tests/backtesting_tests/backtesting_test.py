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

# All test coroutines will be treated as marked.
from octobot_commons.tests.test_config import load_test_config
from octobot_trading.api.exchange import get_exchange_manager_from_exchange_id
from octobot_trading.api.profitability import get_profitability_stats

from octobot.api.backtesting import get_independent_backtesting_exchange_manager_ids
from octobot.backtesting.abstract_backtesting_test import DATA_FILES
from tests.test_utils.bot_management import run_independent_backtesting

BACKTESTING_SYMBOLS = ["ICX/BTC", "VEN/BTC", "XRB/BTC"]

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_backtesting():
    previous_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]])
    current_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]])

    previous_exchange_manager = get_exchange_manager_from_exchange_id(
        get_independent_backtesting_exchange_manager_ids(previous_backtesting)[0])
    current_exchange_manager = get_exchange_manager_from_exchange_id(
        get_independent_backtesting_exchange_manager_ids(current_backtesting)[0])

    _, previous_profitability, previous_market_profitability, _ = get_profitability_stats(previous_exchange_manager)
    _, current_profitability, current_market_profitability, _ = get_profitability_stats(current_exchange_manager)

    # ensure no randomness in backtesting
    assert previous_profitability == current_profitability
    assert previous_market_profitability == current_market_profitability
