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
import mock


def order_mock(**kwargs):
    order = mock.Mock(**kwargs)
    order.is_open = mock.Mock(return_value=True)
    order.is_cancelling = mock.Mock(return_value=False)
    order.trader = mock.Mock()
    order.trader.cancel_order = mock.AsyncMock()
    order.trader.edit_order = mock.AsyncMock()
    order.trader.exchange_manager = mock.Mock(trading_modes=[])
    order.trader.exchange_manager.trader = order.trader
    return order
