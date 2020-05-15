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

from octobot_commons.asyncio_tools import ErrorContainer
from octobot_trading.api.exchange import get_exchange_manager_from_exchange_id
from octobot_trading.api.orders import get_open_orders
from octobot_trading.api.profitability import get_profitability_stats
from octobot.api.backtesting import get_independent_backtesting_exchange_manager_ids, stop_independent_backtesting, \
    check_independent_backtesting_remaining_objects
from octobot.backtesting.abstract_backtesting_test import DATA_FILES
from octobot_trading.api.trades import get_trade_history
from tests.test_utils.bot_management import run_independent_backtesting

BACKTESTING_SYMBOLS = ["ICX/BTC", "VEN/BTC", "XRB/BTC", "2020ADA/BTC", "2020ADA/USDT", "BTC/USDT"]

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_single_data_file_backtesting():
    error_container = ErrorContainer()
    asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
    previous_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]])
    current_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]])

    await _check_backtesting_results(previous_backtesting, current_backtesting, error_container)


async def test_single_data_file_no_logs_backtesting():
    error_container = ErrorContainer()
    asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
    previous_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]], use_loggers=False)
    current_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]], use_loggers=False)

    await _check_backtesting_results(previous_backtesting, current_backtesting, error_container)


async def test_single_data_file_mixed_logs_backtesting():
    error_container = ErrorContainer()
    asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
    previous_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]], use_loggers=False)
    current_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]]], use_loggers=True)

    await _check_backtesting_results(previous_backtesting, current_backtesting, error_container)


async def test_double_synchronized_data_file_backtesting():
    error_container = ErrorContainer()
    asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
    previous_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]],
                                                              DATA_FILES[BACKTESTING_SYMBOLS[1]]],
                                                             timeout=40)
    current_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[0]],
                                                             DATA_FILES[BACKTESTING_SYMBOLS[1]]],
                                                            timeout=40)

    await _check_backtesting_results(previous_backtesting, current_backtesting, error_container)


async def test_double_partially_synchronized_data_file_backtesting_common_only():
    error_container = ErrorContainer()
    asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
    previous_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[3]],
                                                              DATA_FILES[BACKTESTING_SYMBOLS[4]]],
                                                             timeout=40)
    current_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[3]],
                                                             DATA_FILES[BACKTESTING_SYMBOLS[4]]],
                                                            timeout=40)

    await _check_backtesting_results(previous_backtesting, current_backtesting, error_container)


async def test_double_partially_synchronized_data_file_backtesting_all_data_files_range():
    error_container = ErrorContainer()
    asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
    previous_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[3]],
                                                              DATA_FILES[BACKTESTING_SYMBOLS[4]]],
                                                             run_on_common_part_only=False,
                                                             timeout=40)
    current_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[3]],
                                                             DATA_FILES[BACKTESTING_SYMBOLS[4]]],
                                                            run_on_common_part_only=False,
                                                            timeout=40)

    await _check_backtesting_results(previous_backtesting, current_backtesting, error_container)


async def test_double_data_file_3_months_gap_backtesting_all_data_files_range():
    error_container = ErrorContainer()
    asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
    previous_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[5]],
                                                              DATA_FILES[BACKTESTING_SYMBOLS[0]]],
                                                             timeout=80,
                                                             run_on_common_part_only=False)
    current_backtesting = await run_independent_backtesting([DATA_FILES[BACKTESTING_SYMBOLS[5]],
                                                             DATA_FILES[BACKTESTING_SYMBOLS[0]]],
                                                            timeout=80,
                                                            run_on_common_part_only=False)

    await _check_backtesting_results(previous_backtesting, current_backtesting, error_container)


async def _check_backtesting_results(backtesting1, backtesting2, error_container):
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

    await stop_independent_backtesting(backtesting1, memory_check=True)
    await stop_independent_backtesting(backtesting2, memory_check=True)
    asyncio.get_event_loop().call_soon(check_independent_backtesting_remaining_objects, backtesting1)
    asyncio.get_event_loop().call_soon(check_independent_backtesting_remaining_objects, backtesting2)
    await asyncio.create_task(error_container.check())
