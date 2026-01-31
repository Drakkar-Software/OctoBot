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
import pytest
import octobot_trading.personal_data as personal_data
import octobot_trading.enums as enums


@pytest.fixture
def stop_first_strategy():
    return personal_data.StopFirstActiveOrderSwapStrategy(
        123, enums.ActiveOrderSwapTriggerPriceConfiguration.FILLING_PRICE.value
    )


def test_is_priority_order(stop_first_strategy):
    assert stop_first_strategy.swap_timeout == 123
    assert stop_first_strategy.is_priority_order(mock.Mock(order_type=enums.TraderOrderType.STOP_LOSS)) is True
    assert stop_first_strategy.is_priority_order(mock.Mock(order_type=enums.TraderOrderType.SELL_LIMIT)) is False
    assert stop_first_strategy.is_priority_order(mock.Mock(order_type=enums.TraderOrderType.BUY_LIMIT)) is False
