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
import pytest
import mock
import decimal

import octobot_trading.modes.script_keywords as script_keywords
import octobot_trading.modes.script_keywords.basic_keywords.position as position
import octobot_trading.enums as enums
import octobot_trading.constants as constants

from tests import event_loop
from tests.modes.script_keywords import mock_context
from tests.exchanges import backtesting_trader, \
    backtesting_config, backtesting_exchange_manager, fake_backtesting


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=["backtesting_config"])
async def test_average_open_pos_entry(mock_context):
    mock_context.exchange_manager.is_future = False
    with mock.patch.object(position, "get_position",
                           mock.Mock(return_value=(mock.Mock(entry_price=decimal.Decimal("40000"))))) \
         as get_position_mock:
        mock_context.symbol = "ETH/USDT"
        assert await script_keywords.average_open_pos_entry(mock_context, enums.TradeOrderSide.BUY.value) == \
               constants.ZERO
        mock_context.exchange_manager.is_future = True
        mock_context.symbol = "ETH/USDT"
        assert await script_keywords.average_open_pos_entry(mock_context, enums.TradeOrderSide.BUY.value) == \
               decimal.Decimal("40000")
        get_position_mock.assert_called_once_with(mock_context, "ETH/USDT", enums.TradeOrderSide.BUY.value)
        get_position_mock.reset_mock()
        mock_context.symbol = "BTC/USDT"
        assert await script_keywords.average_open_pos_entry(mock_context, enums.TradeOrderSide.BUY.value) == \
               decimal.Decimal("40000")
        get_position_mock.assert_called_once_with(mock_context, "BTC/USDT", enums.TradeOrderSide.BUY.value)
