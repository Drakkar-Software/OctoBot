#  Drakkar-Software OctoBot-Tentacles
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
import mock

import tentacles.Meta.Keywords.scripting_library.orders.order_tags as order_tags
import tentacles.Meta.Keywords.scripting_library.orders.cancelling as cancelling
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants

from tentacles.Meta.Keywords.scripting_library.tests import event_loop, mock_context, \
    skip_if_octobot_trading_mocking_disabled
from tentacles.Meta.Keywords.scripting_library.tests.exchanges import backtesting_trader, backtesting_config, \
    backtesting_exchange_manager, fake_backtesting


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_cancel_orders(mock_context, skip_if_octobot_trading_mocking_disabled):
    # skip_if_octobot_trading_mocking_disabled mock_context.trader, "cancel_order"
    tagged_orders = ["order_1", "order_2"]
    with mock.patch.object(mock_context.trader, "cancel_order",
                           mock.AsyncMock(return_value=True)) as cancel_order_mock, \
         mock.patch.object(mock_context.trader, "cancel_open_orders", mock.AsyncMock(return_value=(True, []))) \
            as cancel_open_orders_mock:
        with mock.patch.object(order_tags, "get_tagged_orders", mock.Mock(return_value=tagged_orders)) \
                as get_tagged_orders_mock:
            # cancel all orders from context symbol
            assert await cancelling.cancel_orders(mock_context) is True
            get_tagged_orders_mock.assert_not_called()
            cancel_order_mock.assert_not_called()
            cancel_open_orders_mock.assert_called_once_with(
                mock_context.symbol, cancel_loaded_orders=True, side=None,
                since=trading_constants.NO_DATA_LIMIT,
                until=trading_constants.NO_DATA_LIMIT
            )
            cancel_open_orders_mock.reset_mock()

            # cancel sided orders from context symbol
            side_str_to_side = {
                "sell": trading_enums.TradeOrderSide.SELL,
                "buy": trading_enums.TradeOrderSide.BUY,
                "all": None,
            }
            for side, value in side_str_to_side.items():
                assert await cancelling.cancel_orders(mock_context, which=side, cancel_loaded_orders=False) is True
                get_tagged_orders_mock.assert_not_called()
                cancel_order_mock.assert_not_called()
                cancel_open_orders_mock.assert_called_once_with(
                    mock_context.symbol, cancel_loaded_orders=False, side=value,
                    since=trading_constants.NO_DATA_LIMIT,
                    until=trading_constants.NO_DATA_LIMIT
                )
                cancel_open_orders_mock.reset_mock()

            # different symbol values
            assert await cancelling.cancel_orders(mock_context, symbol="ETH/USDT") is True
            get_tagged_orders_mock.assert_not_called()
            cancel_order_mock.assert_not_called()
            cancel_open_orders_mock.assert_called_once_with(
                "ETH/USDT", cancel_loaded_orders=True, side=value,
                since=trading_constants.NO_DATA_LIMIT,
                until=trading_constants.NO_DATA_LIMIT
            )
            cancel_open_orders_mock.reset_mock()
            assert await cancelling.cancel_orders(mock_context, symbols=["ETH/USDT", "USDT/USDC"]) is True
            get_tagged_orders_mock.assert_not_called()
            cancel_order_mock.assert_not_called()
            assert cancel_open_orders_mock.mock_calls[0].args == ("ETH/USDT", )
            assert cancel_open_orders_mock.mock_calls[1].args == ("USDT/USDC", )
            cancel_open_orders_mock.reset_mock()

            # tags
            assert await cancelling.cancel_orders(mock_context, which="tag1") is True
            get_tagged_orders_mock.assert_called_once_with(
                mock_context, "tag1", symbol=None,
                since=trading_constants.NO_DATA_LIMIT,
                until=trading_constants.NO_DATA_LIMIT
            )
            assert cancel_order_mock.mock_calls[0].args == ("order_1", )
            assert cancel_order_mock.mock_calls[1].args == ("order_2", )
            cancel_open_orders_mock.assert_not_called()
            cancel_order_mock.reset_mock()

        # no order to cancel
        with mock.patch.object(order_tags, "get_tagged_orders", mock.Mock(return_value=[])) as get_tagged_orders_mock:
            assert await cancelling.cancel_orders(mock_context, which="tag1") is False
            get_tagged_orders_mock.assert_called_once_with(
                mock_context, "tag1", symbol=None,
                since=trading_constants.NO_DATA_LIMIT,
                until=trading_constants.NO_DATA_LIMIT
            )
            cancel_order_mock.assert_not_called()
            cancel_open_orders_mock.assert_not_called()
