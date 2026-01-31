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
import decimal

import pytest_asyncio

import octobot_commons.constants as commons_constants
import octobot_commons.symbols.symbol_util as symbol_util
from octobot_commons.tests.test_config import load_test_config
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.exchange_data.contracts as contracts
from octobot_trading.exchanges.traders.trader_simulator import TraderSimulator
from octobot_trading.exchanges.traders.trader import Trader


async def create_trader_from_exchange_manager(exchange_manager, simulated=False, contract=None):
    config = load_test_config()
    if simulated:
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_ENABLED_OPTION] = True
        trader_inst = TraderSimulator(load_test_config(), exchange_manager)
    else:
        config[commons_constants.CONFIG_TRADER][commons_constants.CONFIG_ENABLED_OPTION] = True
        trader_inst = Trader(load_test_config(), exchange_manager)
    await trader_inst.initialize()
    if contract is not None:
        return config, exchange_manager, trader_inst, contract
    return config, exchange_manager, trader_inst


@pytest_asyncio.fixture
async def trader(exchange_manager):
    return await create_trader_from_exchange_manager(exchange_manager)


@pytest_asyncio.fixture
async def margin_trader(margin_exchange_manager):
    return await create_trader_from_exchange_manager(margin_exchange_manager)


@pytest_asyncio.fixture
async def future_trader(future_exchange_manager):
    return await create_trader_from_exchange_manager(future_exchange_manager)


@pytest_asyncio.fixture
async def trader_simulator(simulated_exchange_manager):
    return await create_trader_from_exchange_manager(simulated_exchange_manager, simulated=True)


@pytest_asyncio.fixture
async def margin_trader_simulator(margin_simulated_exchange_manager):
    return await create_trader_from_exchange_manager(margin_simulated_exchange_manager, simulated=True)


DEFAULT_FUTURE_SYMBOL = str(symbol_util.parse_symbol("BTC/USDT:USDT"))
DEFAULT_FUTURE_FUNDING_RATE = decimal.Decimal('0.01')
DEFAULT_FUTURE_SYMBOL_LEVERAGE = constants.ONE
DEFAULT_FUTURE_SYMBOL_MAX_LEVERAGE = constants.ONE_HUNDRED
DEFAULT_FUTURE_SYMBOL_MARGIN_TYPE = enums.MarginType.ISOLATED


def get_default_future_inverse_contract():
    return contracts.FutureContract(
        pair=DEFAULT_FUTURE_SYMBOL,
        margin_type=DEFAULT_FUTURE_SYMBOL_MARGIN_TYPE,
        contract_type=enums.FutureContractType.INVERSE_PERPETUAL,
        current_leverage=DEFAULT_FUTURE_SYMBOL_LEVERAGE,
        maximum_leverage=DEFAULT_FUTURE_SYMBOL_MAX_LEVERAGE)


def get_default_future_linear_contract():
    return contracts.FutureContract(
        pair=DEFAULT_FUTURE_SYMBOL,
        margin_type=DEFAULT_FUTURE_SYMBOL_MARGIN_TYPE,
        contract_type=enums.FutureContractType.LINEAR_PERPETUAL,
        current_leverage=DEFAULT_FUTURE_SYMBOL_LEVERAGE,
        maximum_leverage=DEFAULT_FUTURE_SYMBOL_MAX_LEVERAGE)


@pytest_asyncio.fixture
async def future_trader_simulator_with_default_inverse(future_simulated_exchange_manager):
    contract = get_default_future_inverse_contract()
    future_simulated_exchange_manager.exchange.set_pair_future_contract(DEFAULT_FUTURE_SYMBOL, contract)
    return await create_trader_from_exchange_manager(future_simulated_exchange_manager,
                                                     simulated=True,
                                                     contract=contract)


@pytest_asyncio.fixture
async def future_trader_simulator_with_default_linear(future_simulated_exchange_manager):
    contract = get_default_future_linear_contract()
    future_simulated_exchange_manager.exchange.set_pair_future_contract(DEFAULT_FUTURE_SYMBOL, contract)
    return await create_trader_from_exchange_manager(future_simulated_exchange_manager,
                                                     simulated=True,
                                                     contract=contract)
