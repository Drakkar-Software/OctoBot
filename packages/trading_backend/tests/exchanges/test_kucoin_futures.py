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
from tests import kucoinfutures_exchange


def test_get_name(kucoinfutures_exchange):
    assert exchanges.KucoinFutures(kucoinfutures_exchange).get_name() == ccxt.async_support.kucoinfutures().id.lower()


@pytest.mark.asyncio
async def test_broker_id(kucoinfutures_exchange):
    exchange = exchanges.KucoinFutures(kucoinfutures_exchange)
    exchange._exchange.exchange_manager.is_future = True
    await create_order_tests.sign_test(
        exchange,
        "futuresPrivate",
        "KC-API-PARTNER",
        broker_sign_header_key="KC-API-PARTNER-SIGN",
    )
