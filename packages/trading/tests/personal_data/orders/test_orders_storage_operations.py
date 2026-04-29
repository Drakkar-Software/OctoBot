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
import mock
import pytest
import pytest_asyncio
import decimal

import octobot_trading.enums as enums
import octobot_trading.personal_data as personal_data
import octobot_trading.constants as constants

from tests import event_loop
from tests.exchanges import exchange_manager, simulated_exchange_manager
from tests.exchanges.traders import trader_simulator
from tests.exchanges.traders import trader

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
def initialized_mocked_order_storage(trader_simulator):
    config, exchange_manager_inst, trader_inst = trader_simulator
    mocked_order_storage = mock.Mock(
        stop=mock.AsyncMock(),
    )
    exchange_manager_inst.storage_manager.orders_storage = mocked_order_storage
    yield mocked_order_storage, exchange_manager_inst, trader_inst


async def test_apply_order_storage_details_if_any(initialized_mocked_order_storage):
    mocked_order_storage, exchange_manager_inst, trader_inst = initialized_mocked_order_storage
    mocked_order_storage.get_startup_order_details = mock.AsyncMock(return_value={})
    mocked_order_storage.should_store_data = mock.Mock(return_value=False)

    order = personal_data.BuyLimitOrder(trader_inst)
    order.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                 symbol="BTC/USDT",
                 current_price=decimal.Decimal("70"),
                 quantity=decimal.Decimal("10"),
                 price=decimal.Decimal("70"),
                 exchange_order_id="plop exchange_id")
    await personal_data.apply_order_storage_details_if_any(order, exchange_manager_inst, {})
    # disabled in trader simulator
    mocked_order_storage.get_startup_order_details.assert_not_awaited()

    mocked_order_storage.should_store_data = mock.Mock(return_value=True)
    await personal_data.apply_order_storage_details_if_any(order, exchange_manager_inst, {})
    mocked_order_storage.get_startup_order_details.assert_awaited_once_with("plop exchange_id")

    # ensure no crash with not well formatted order_details
    mocked_order_storage.get_startup_order_details = mock.AsyncMock(return_value={"hello": "hi there"})
    await personal_data.apply_order_storage_details_if_any(order, exchange_manager_inst, {})
    mocked_order_storage.get_startup_order_details.assert_awaited_once_with("plop exchange_id")

    # ensure order update is done
    assert order.order_id != "new id 123"
    assert order.exchange_order_id != "new exchange id 123"
    mocked_order_storage.get_startup_order_details = mock.AsyncMock(return_value={
        constants.STORAGE_ORIGIN_VALUE: {
            enums.ExchangeConstantsOrderColumns.ID.value: "new id 123",
            enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "new exchange id 123"
        }
    })
    await personal_data.apply_order_storage_details_if_any(order, exchange_manager_inst, {})
    mocked_order_storage.get_startup_order_details.assert_awaited_once_with("plop exchange_id")
    assert order.order_id == "new id 123"
    assert order.exchange_order_id == "new exchange id 123"
