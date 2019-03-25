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


import ccxt
import pytest

from config import SIMULATOR_INITIAL_STARTUP_PORTFOLIO, SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE, \
    REAL_INITIAL_STARTUP_PORTFOLIO, REAL_INITIAL_STARTUP_PORTFOLIO_VALUE, WATCHED_MARKETS_INITIAL_STARTUP_VALUES, \
    REFERENCE_MARKET, SIMULATOR_CURRENT_PORTFOLIO
from trading.exchanges.exchange_manager import ExchangeManager
from trading.trader.previous_trading_state_manager import PreviousTradingStateManager
from tests.test_utils.config import load_test_config
from tests.test_utils.config import TEST_CONFIG_FOLDER


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

TESTS_STATE_SAVE_FOLDER = f"{TEST_CONFIG_FOLDER}/trading_states_tests/"


async def init_default():
    config = load_test_config()
    exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
    await exchange_manager.initialize()
    exchange_inst = exchange_manager.get_exchange()
    return config, exchange_inst


async def test_load_ok_file_no_trades():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ok_ref.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert state_manager.get_previous_state(exchange_inst, SIMULATOR_CURRENT_PORTFOLIO) == {
        "BTC": 100,
        "USD": 9999
    }
    assert state_manager.get_previous_state(exchange_inst, SIMULATOR_INITIAL_STARTUP_PORTFOLIO) == {
        "BTC": 10,
        "USD": 1000
    }
    assert state_manager.get_previous_state(exchange_inst, REAL_INITIAL_STARTUP_PORTFOLIO) == {
        "ZYX": 9999,
        "DAI": 1
    }
    assert state_manager.get_previous_state(exchange_inst, SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE) == 10
    assert state_manager.get_previous_state(exchange_inst, REAL_INITIAL_STARTUP_PORTFOLIO_VALUE) == 100
    assert state_manager.get_previous_state(exchange_inst, WATCHED_MARKETS_INITIAL_STARTUP_VALUES) == {
        "BTC": 1,
        "USDT": 0.00025075791580050704,
        "XLM": 10,
        "ETC": 10,
        "XRB": 10,
        "VEN": 10,
        "ONT": 10,
        "XRP": 10,
        "NEO": 10,
        "ADA": 10,
        "EUR": 10,
        "POWR": 10,
        "WAX": 10,
        "ICX": 10,
        "XVG": 10,
        "ETH": 10
    }
    assert state_manager.get_previous_state(exchange_inst, REFERENCE_MARKET) == "BTC"
