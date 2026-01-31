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

import pytest

import octobot_trading.enums as enums
import octobot_trading.exchange_data.contracts as contracts

from tests import event_loop

pytestmark = pytest.mark.asyncio

DEFAULT_SYMBOL = "BTC/USDT"


async def test_is_inverse_contract():
    contract = contracts.FutureContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        contract_type=enums.FutureContractType.INVERSE_PERPETUAL,
        current_leverage=decimal.Decimal(10))
    assert contract.is_inverse_contract()
    contract = contracts.FutureContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        contract_type=enums.FutureContractType.LINEAR_PERPETUAL,
        current_leverage=decimal.Decimal(10))
    assert not contract.is_inverse_contract()


async def test_is_perpetual_contract():
    contract = contracts.FutureContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        contract_type=enums.FutureContractType.INVERSE_PERPETUAL,
        current_leverage=decimal.Decimal(10))
    assert contract.is_perpetual_contract()
    contract = contracts.FutureContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        contract_type=enums.FutureContractType.LINEAR_EXPIRABLE,
        current_leverage=decimal.Decimal(10))
    assert not contract.is_perpetual_contract()


async def test_is_one_way_position_mode():
    contract = contracts.FutureContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        position_mode=enums.PositionMode.ONE_WAY,
        contract_type=enums.FutureContractType.INVERSE_PERPETUAL,
        current_leverage=decimal.Decimal(10))
    assert contract.is_one_way_position_mode()
    contract = contracts.FutureContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        position_mode=enums.PositionMode.HEDGE,
        contract_type=enums.FutureContractType.INVERSE_PERPETUAL,
        current_leverage=decimal.Decimal(10))
    assert not contract.is_one_way_position_mode()


async def test_set_position_mode():
    contract = contracts.FutureContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        contract_type=enums.FutureContractType.INVERSE_PERPETUAL,
        current_leverage=decimal.Decimal(10))
    assert contract.position_mode == enums.PositionMode.ONE_WAY
    contract.set_position_mode(is_one_way=True)
    assert contract.position_mode == enums.PositionMode.ONE_WAY
    contract.set_position_mode(is_hedge=False)
    assert contract.position_mode == enums.PositionMode.ONE_WAY
    contract.set_position_mode(is_one_way=False)
    assert contract.position_mode == enums.PositionMode.HEDGE
    contract.set_position_mode(is_hedge=False)
    assert contract.position_mode == enums.PositionMode.ONE_WAY
    contract.set_position_mode(is_hedge=True)
    assert contract.position_mode == enums.PositionMode.HEDGE
