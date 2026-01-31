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
import mock
import pytest
import ccxt.async_support
import trading_backend.exchanges as exchanges
import tests.util.create_order_tests as create_order_tests
import tests.util.account_tests as account_tests
from tests import okx_exchange


def test_get_name(okx_exchange):
    assert exchanges.OKX(okx_exchange).get_name() == ccxt.async_support.okx().id.lower()


@pytest.mark.asyncio
async def test_get_orders_parameters(okx_exchange):
    exchange = exchanges.OKX(okx_exchange)
    await create_order_tests.create_order_mocked_test_args(
        exchange,
        exchange_private_post_order_method_name="privatePostTradeBatchOrders",
        exchange_request_referral_key="tag",
        should_contains=False,
        result_is_list=True,
        post_order_mock_return_value={'data': [{}]}
    )


@pytest.mark.asyncio
async def test_invalid_api_key(okx_exchange):
    exchange = exchanges.OKX(okx_exchange)
    await account_tests.check_invalid_account(exchange)


@pytest.mark.asyncio
async def test_invalid_api_key_get_api_key_rights(okx_exchange):
    exchange = exchanges.OKX(okx_exchange)
    await account_tests.check_invalid_account_keys_rights(exchange)
