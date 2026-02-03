
#  Copyright (c) Drakkar-Software, All rights reserved.
#  Drakkar-Software trading-backend
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
import ccxt.async_support
import trading_backend.exchanges as exchanges
import tests.util.create_order_tests as create_order_tests
import tests.util.account_tests as account_tests
from tests import bingx_exchange


def test_get_name(bingx_exchange):
    assert exchanges.Bingx(bingx_exchange).get_name() == ccxt.async_support.bingx().id.lower()


@pytest.mark.asyncio
async def test_sign(bingx_exchange):
    exchange = exchanges.Bingx(bingx_exchange)
    await create_order_tests.sign_test(
        exchange,
        None,
        "X-SOURCE-KEY",
        section=['spot', 'v1', 'private']
    )


@pytest.mark.asyncio
async def test_invalid_api_key(bingx_exchange):
    exchange = exchanges.Bingx(bingx_exchange)
    await account_tests.check_invalid_account(exchange)


@pytest.mark.asyncio
async def test_invalid_api_key_get_api_key_rights(bingx_exchange):
    exchange = exchanges.Bingx(bingx_exchange)
    await account_tests.check_invalid_account_keys_rights(exchange)
