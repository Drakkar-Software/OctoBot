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
import ccxt.async_support
import pytest

import trading_backend.exchanges as exchanges
import tests.util.create_order_tests as create_order_tests
from tests import bybit_exchange


def test_get_name(bybit_exchange):
    assert exchanges.Bybit(bybit_exchange).get_name() == ccxt.async_support.bybit().id.lower()


@pytest.mark.asyncio
async def test_future_orders_parameters(bybit_exchange):
    exchange = exchanges.Bybit(bybit_exchange)
    await create_order_tests.create_order_mocked_test_args(
        exchange,
        symbol="BTC/USDT:USDT",
        exchange_private_post_order_method_name="privatePostPrivateLinearStopOrderCreate",
        exchange_request_referral_key=exchange.HEADER_SPOT_KEY,
        should_contains=False)


@pytest.mark.asyncio
async def test_future_orders_parameters(bybit_exchange):
    bybit_exchange.exchange_manager.is_future = True
    exchange = exchanges.Bybit(bybit_exchange)
    assert exchange.get_headers() == {exchange.HEADER_FUTURE_KEY: exchange._get_id()}
    await create_order_tests.exchange_requests_contains_headers_test(
        exchange,
        exchange_header_referral_key=exchange.HEADER_FUTURE_KEY,
        exchange_header_referral_value=exchange._get_id())
