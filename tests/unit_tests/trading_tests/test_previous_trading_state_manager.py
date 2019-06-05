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
from os import path
from shutil import copyfile
import json

from config import SIMULATOR_INITIAL_STARTUP_PORTFOLIO, SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE, \
    REAL_INITIAL_STARTUP_PORTFOLIO, REAL_INITIAL_STARTUP_PORTFOLIO_VALUE, WATCHED_MARKETS_INITIAL_STARTUP_VALUES, \
    REFERENCE_MARKET, SIMULATOR_CURRENT_PORTFOLIO, CONFIG_TRADING, CONFIG_ENABLED_PERSISTENCE, CONFIG_TRADER, \
    CONFIG_ENABLED_OPTION
from octobot_trading.exchanges import ExchangeManager
from trading.trader.previous_trading_state_manager import PreviousTradingStateManager
from tests.test_utils.config import load_test_config
from tests.test_utils.config import TEST_CONFIG_FOLDER
from trading.trader.portfolio import Portfolio


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

TESTS_STATE_SAVE_FOLDER = f"{TEST_CONFIG_FOLDER}/trading_states_tests/"


async def init_default():
    config = load_test_config()
    exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
    await exchange_manager.initialize()
    exchange_inst = exchange_manager.get_exchange()
    return config, exchange_inst


async def test_enabled():
    config, _ = await init_default()
    assert not PreviousTradingStateManager.enabled(config)
    config[CONFIG_TRADING][CONFIG_ENABLED_PERSISTENCE] = True
    assert PreviousTradingStateManager.enabled(config)


async def test_load_ok_file():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ok_ref.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert not state_manager.first_data

    assert state_manager.has_previous_state(exchange_inst)

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


async def test_load_ok_file_2():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ok_ref.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok2_log")
    assert not state_manager.first_data
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


async def test_update_state():
    config, exchange_inst = await init_default()
    e_name = exchange_inst.get_name()

    copyfile(f"{TESTS_STATE_SAVE_FOLDER}ok_ref.json", f"{TESTS_STATE_SAVE_FOLDER}to_modify.json")
    state_manager = PreviousTradingStateManager({e_name: None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}to_modify.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    state_manager.update_previous_states(exchange_inst, simulated_initial_portfolio={
        "BTC": {
            Portfolio.AVAILABLE: 10,
            Portfolio.TOTAL: 200
        }
    })
    assert state_manager.get_previous_state(exchange_inst, SIMULATOR_INITIAL_STARTUP_PORTFOLIO) == {
        "BTC": 200
    }
    state_manager.update_previous_states(exchange_inst, real_initial_portfolio={
        "BTC": {
            Portfolio.AVAILABLE: 10,
            Portfolio.TOTAL: 250
        }
    })
    assert state_manager.get_previous_state(exchange_inst, REAL_INITIAL_STARTUP_PORTFOLIO) == {
        "BTC": 250
    }
    state_manager.update_previous_states(exchange_inst, simulated_initial_portfolio_value=10)
    assert state_manager.get_previous_state(exchange_inst, SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE) == 10
    state_manager.update_previous_states(exchange_inst, real_initial_portfolio_value=100)
    assert state_manager.get_previous_state(exchange_inst, REAL_INITIAL_STARTUP_PORTFOLIO_VALUE) == 100
    state_manager.update_previous_states(exchange_inst, watched_markets_initial_values="xyz")
    assert state_manager.get_previous_state(exchange_inst, WATCHED_MARKETS_INITIAL_STARTUP_VALUES) == "xyz"
    state_manager.update_previous_states(exchange_inst, reference_market="LOL")
    assert state_manager.get_previous_state(exchange_inst, REFERENCE_MARKET) == "LOL"

    with open(f"{TESTS_STATE_SAVE_FOLDER}to_modify.json") as f:
        file_content = json.loads(f.read())
    assert file_content[e_name][SIMULATOR_INITIAL_STARTUP_PORTFOLIO] == {"BTC": 200}
    assert file_content[e_name][REAL_INITIAL_STARTUP_PORTFOLIO] == {"BTC": 250}
    assert file_content[e_name][SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE] == 10
    assert file_content[e_name][REAL_INITIAL_STARTUP_PORTFOLIO_VALUE] == 100
    assert file_content[e_name][WATCHED_MARKETS_INITIAL_STARTUP_VALUES] == "xyz"
    assert file_content[e_name][REFERENCE_MARKET] == "LOL"

    state_manager.reset_trading_history()


async def test_reset_history():
    config, exchange_inst = await init_default()
    copyfile(f"{TESTS_STATE_SAVE_FOLDER}ok_ref.json", f"{TESTS_STATE_SAVE_FOLDER}to_reset.json")
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}to_reset.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert not state_manager.first_data
    state_manager.reset_trading_history()

    assert not path.exists(f"{TESTS_STATE_SAVE_FOLDER}to_reset.json")

    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}to_reset.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert state_manager.first_data
    assert state_manager.should_initialize_data()


async def test_load_ko_file_1():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ko_ref_invalid_json.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert state_manager.first_data


async def test_load_ko_file_2():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ko_ref_symbols_changed.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert state_manager.first_data


async def test_load_ko_file_3():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ko_ref_ref_market_changed.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert state_manager.first_data


async def test_load_ko_file_4():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ko_ref_missing_key.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert state_manager.first_data


async def test_load_ko_file_5():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ko_ref_missing_exchange.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert state_manager.first_data


async def test_load_ko_file_6():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}NO_EXISTS.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert state_manager.first_data


async def test_load_ko_file_7():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ok_ref.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ko_log")
    assert state_manager.first_data


async def test_load_ko_file_8():
    config, exchange_inst = await init_default()
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ko_missing_trader_s_data.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert state_manager.first_data


async def test_load_ko_file_9():
    config, exchange_inst = await init_default()
    config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = True
    state_manager = PreviousTradingStateManager({exchange_inst.get_name(): None}, False, config,
                                                save_file=f"{TESTS_STATE_SAVE_FOLDER}ko_missing_trader_data.json",
                                                log_file=f"{TESTS_STATE_SAVE_FOLDER}ok_log")
    assert state_manager.first_data
