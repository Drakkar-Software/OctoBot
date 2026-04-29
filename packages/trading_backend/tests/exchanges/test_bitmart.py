#  Drakkar-Software trading-backend
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
import ccxt.async_support
import trading_backend.exchanges as exchanges
import tests.util.create_order_tests as create_order_tests
from tests import bitmart_exchange


def test_get_name(bitmart_exchange):
    assert exchanges.Bitmart(bitmart_exchange).get_name() == ccxt.async_support.bitmart().id.lower()


@pytest.mark.asyncio
async def test_sign(bitmart_exchange):
    exchange = exchanges.Bitmart(bitmart_exchange)
    exchange._exchange.connector.client.uid = "uid"
    exchange._exchange.connector.client.apiKey = "apiKey"
    exchange._exchange.connector.client.secret = "secret"
    await create_order_tests.sign_test(
        exchange,
        "private",
        "X-BM-BROKER-ID",
        should_contains=False,
        url_path="spot/v3/orders"
    )
