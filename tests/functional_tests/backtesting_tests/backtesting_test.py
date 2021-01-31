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
import asyncio
import pytest

import octobot_commons.asyncio_tools as asyncio_tools
from octobot_trading.api.exchange import get_exchange_manager_from_exchange_id
from octobot_trading.api.orders import get_open_orders
from octobot_trading.api.profitability import get_profitability_stats
from octobot.api.backtesting import get_independent_backtesting_exchange_manager_ids, stop_independent_backtesting, \
    check_independent_backtesting_remaining_objects
from octobot.backtesting.abstract_backtesting_test import DATA_FILES
from octobot_trading.api.trades import get_trade_history
from tests.test_utils.bot_management import run_independent_backtesting
from tests.test_utils.logging import activate_tentacles_loading_logger

activate_tentacles_loading_logger()
# force tentacles import since it's required for backtesting
import tentacles

BACKTESTING_SYMBOLS = ["ICX/BTC", "VEN/BTC", "XRB/BTC", "2020ADA/BTC", "2020ADA/USDT", "BTC/USDT"]

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


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


async def test_single_data_file_backtesting():
    await _check_double_backtesting(
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]]),
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]])
    )


async def test_single_data_file_no_logs_backtesting():
    await _check_double_backtesting(
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]], use_loggers=False),
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]], use_loggers=False)
    )


async def test_single_data_file_mixed_logs_backtesting():
    await _check_double_backtesting(
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]], use_loggers=False),
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]], use_loggers=True)
    )


async def test_double_synchronized_data_file_backtesting():
    await _check_double_backtesting(
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]],
                                     DATA_FILES[BACKTESTING_SYMBOLS[1]]],
                                    timeout=40),
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]],
                                     DATA_FILES[BACKTESTING_SYMBOLS[1]]],
                                    timeout=40)
    )


async def test_double_partially_synchronized_data_file_backtesting_common_only():
    await _check_double_backtesting(
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[3]],
                                     DATA_FILES[BACKTESTING_SYMBOLS[4]]],
                                    timeout=40),
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[3]],
                                     DATA_FILES[BACKTESTING_SYMBOLS[4]]],
                                    timeout=40)
    )


async def test_double_partially_synchronized_data_file_backtesting_all_data_files_range():
    await _check_double_backtesting(
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[3]],
                                     DATA_FILES[BACKTESTING_SYMBOLS[4]]],
                                    run_on_common_part_only=False,
                                    timeout=40),
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[3]],
                                     DATA_FILES[BACKTESTING_SYMBOLS[4]]],
                                    run_on_common_part_only=False,
                                    timeout=40)
    )


async def test_double_data_file_3_months_gap_backtesting_all_data_files_range():
    await _check_double_backtesting(
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[5]],
                                     DATA_FILES[BACKTESTING_SYMBOLS[0]]],
                                    run_on_common_part_only=False,
                                    timeout=80),
        run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[5]],
                                     DATA_FILES[BACKTESTING_SYMBOLS[0]]],
                                    run_on_common_part_only=False,
                                    timeout=80)
    )


async def _check_double_backtesting(backtesting_coro1, backtesting_coro2):
    backtesting1 = None
    backtesting2 = None
    try:
        backtesting1 = await backtesting_coro1
        backtesting2 = await backtesting_coro2
    finally:
        await _check_backtesting_results(backtesting1, backtesting2)


async def _check_backtesting_results(backtesting1, backtesting2):
    if backtesting1 is not None and backtesting2 is not None:
        exchange_manager_1 = get_exchange_manager_from_exchange_id(
            get_independent_backtesting_exchange_manager_ids(backtesting1)[0])
        exchange_manager_2 = get_exchange_manager_from_exchange_id(
            get_independent_backtesting_exchange_manager_ids(backtesting2)[0])

        _, previous_profitability, previous_market_profitability, _, _ = get_profitability_stats(exchange_manager_1)
        _, current_profitability, current_market_profitability, _, _ = get_profitability_stats(exchange_manager_2)

        trades = get_trade_history(exchange_manager_1)
        open_orders = get_open_orders(exchange_manager_1)
        # ensure at least one order is either open or got filled
        assert trades + open_orders

        trades = open_orders = exchange_manager_1 = exchange_manager_2 = None  # prevent memory leak

        # ensure no randomness in backtesting
        assert previous_profitability == current_profitability
        assert current_profitability != 0
        assert previous_profitability != 0
        assert previous_market_profitability == current_market_profitability

    backtestings = tuple(b for b in (backtesting1, backtesting2) if b is not None)
    for backtesting in backtestings:
        await stop_independent_backtesting(backtesting, memory_check=True, should_raise=True)
        await asyncio.wait_for(backtesting.post_backtesting_task, 5)
    for backtesting in backtestings:
        asyncio.get_event_loop().call_soon(check_independent_backtesting_remaining_objects, backtesting)
