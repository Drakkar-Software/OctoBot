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
import os

import pytest

import octobot_trading.errors as errors
import octobot_trading.enums as enums
import octobot_trading.exchange_data.contracts as contracts

from tests import event_loop

pytestmark = pytest.mark.asyncio

DEFAULT_SYMBOL = "BTC/USDT"


async def test_is_isolated():
    contract = contracts.MarginContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        current_leverage=decimal.Decimal(10))
    assert contract.is_isolated()
    contract = contracts.MarginContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.CROSS,
        current_leverage=decimal.Decimal(10))
    assert not contract.is_isolated()


async def test_set_current_leverage():
    contract = contracts.MarginContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        maximum_leverage=None,
        current_leverage=decimal.Decimal(10))
    assert contract.current_leverage == decimal.Decimal(10)
    assert contract.maximum_leverage is None
    contract.set_current_leverage(decimal.Decimal(50))
    assert contract.current_leverage == decimal.Decimal(50)
    contract = contracts.MarginContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        maximum_leverage=decimal.Decimal(100),
        current_leverage=decimal.Decimal(10))
    assert contract.current_leverage == decimal.Decimal(10)
    contract.set_current_leverage(decimal.Decimal(50))
    assert contract.current_leverage == decimal.Decimal(50)


async def test_set_margin_type():
    contract = contracts.MarginContract(
        pair=DEFAULT_SYMBOL,
        margin_type=enums.MarginType.ISOLATED,
        current_leverage=decimal.Decimal(10))
    assert contract.margin_type == enums.MarginType.ISOLATED
    contract.set_margin_type(is_isolated=True)
    assert contract.margin_type == enums.MarginType.ISOLATED
    contract.set_margin_type(is_cross=False)
    assert contract.margin_type == enums.MarginType.ISOLATED
    contract.set_margin_type(is_isolated=False)
    assert contract.margin_type == enums.MarginType.CROSS
    contract.set_margin_type(is_cross=False)
    assert contract.margin_type == enums.MarginType.ISOLATED
    contract.set_margin_type(is_cross=True)
    assert contract.margin_type == enums.MarginType.CROSS

