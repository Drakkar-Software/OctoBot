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
import decimal

import octobot_trading.enums as trading_enums
import octobot_trading.errors as errors
import octobot_trading.modes.script_keywords as script_keywords
import tentacles.Meta.Keywords.scripting_library.orders.position_size.target_position as target_position
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_private_data as exchange_private_data

from tentacles.Meta.Keywords.scripting_library.tests import event_loop, mock_context
from tentacles.Meta.Keywords.scripting_library.tests.exchanges import backtesting_trader, backtesting_config, \
    backtesting_exchange_manager, fake_backtesting


def test_get_target_position_side():
    assert target_position.get_target_position_side(1) == trading_enums.TradeOrderSide.BUY.value
    assert target_position.get_target_position_side(-1) == trading_enums.TradeOrderSide.SELL.value
    with pytest.raises(RuntimeError):
        target_position.get_target_position_side(0)


@pytest.mark.asyncio
async def test_get_target_position(mock_context):
    with pytest.raises(errors.InvalidArgumentError):
        await target_position.get_target_position(mock_context, "1sdsqdq")

    # with positive (long) position
    with mock.patch.object(script_keywords, "adapt_amount_to_holdings",
                           mock.AsyncMock(return_value=decimal.Decimal(1))) as adapt_amount_to_holdings_mock, \
         mock.patch.object(exchange_private_data, "open_position_size",
                              mock.Mock(return_value=decimal.Decimal(10))) as open_position_size_mock:

        with mock.patch.object(script_keywords, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.POSITION_PERCENT, decimal.Decimal(10)))) \
                as parse_quantity_mock, \
             mock.patch.object(target_position, "get_target_position_side",
                               mock.Mock(return_value=trading_enums.TradeOrderSide.SELL.value)) \
                as get_target_position_side_mock:
            assert await target_position.get_target_position(mock_context, "1", target_price="hello") == \
                   (decimal.Decimal(1), trading_enums.TradeOrderSide.SELL.value)
            parse_quantity_mock.assert_called_once_with("1")
            open_position_size_mock.assert_called_once_with(mock_context)
            get_target_position_side_mock.assert_called_once_with(decimal.Decimal(-9))
            adapt_amount_to_holdings_mock.assert_called_once_with(mock_context, decimal.Decimal(9),
                                                                  trading_enums.TradeOrderSide.SELL.value,
                                                                  False, True, False, target_price="hello")
            adapt_amount_to_holdings_mock.reset_mock()
            get_target_position_side_mock.reset_mock()
            open_position_size_mock.reset_mock()

        with mock.patch.object(script_keywords, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.PERCENT, decimal.Decimal(110)))) \
                as parse_quantity_mock, \
             mock.patch.object(script_keywords, "total_account_balance",
                               mock.AsyncMock(return_value=decimal.Decimal(10))) \
                as total_account_balance_mock, \
             mock.patch.object(target_position, "get_target_position_side",
                               mock.Mock(return_value=trading_enums.TradeOrderSide.BUY.value)) \
                as get_target_position_side_mock:
            assert await target_position.get_target_position(mock_context, "1", use_total_holding=True,
                                                             reduce_only=False, is_stop_order=True) == \
                   (decimal.Decimal(1), trading_enums.TradeOrderSide.BUY.value)
            parse_quantity_mock.assert_called_once_with("1")
            total_account_balance_mock.assert_called_once_with(mock_context)
            open_position_size_mock.assert_called_once_with(mock_context)
            get_target_position_side_mock.assert_called_once_with(decimal.Decimal(1))
            adapt_amount_to_holdings_mock.assert_called_once_with(mock_context, decimal.Decimal(1),
                                                                  trading_enums.TradeOrderSide.BUY.value,
                                                                  True, False, True, target_price=None)
            adapt_amount_to_holdings_mock.reset_mock()
            get_target_position_side_mock.reset_mock()
            open_position_size_mock.reset_mock()

        with mock.patch.object(script_keywords, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.FLAT, decimal.Decimal(-3)))) \
                as parse_quantity_mock, \
             mock.patch.object(target_position, "get_target_position_side",
                               mock.Mock(return_value=trading_enums.TradeOrderSide.SELL.value)) \
                as get_target_position_side_mock:
            assert await target_position.get_target_position(mock_context, "1") == \
                   (decimal.Decimal(1), trading_enums.TradeOrderSide.SELL.value)
            parse_quantity_mock.assert_called_once_with("1")
            open_position_size_mock.assert_called_once_with(mock_context)
            get_target_position_side_mock.assert_called_once_with(decimal.Decimal(-13))
            adapt_amount_to_holdings_mock.assert_called_once_with(mock_context, decimal.Decimal(13),
                                                                  trading_enums.TradeOrderSide.SELL.value,
                                                                  False, True, False, target_price=None)
            adapt_amount_to_holdings_mock.reset_mock()
            get_target_position_side_mock.reset_mock()
            open_position_size_mock.reset_mock()

        with mock.patch.object(script_keywords, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.AVAILABLE_PERCENT, decimal.Decimal(25)))) \
                as parse_quantity_mock, \
             mock.patch.object(script_keywords, "available_account_balance",
                               mock.AsyncMock(return_value=decimal.Decimal(5))) \
                as available_account_balance_mock, \
             mock.patch.object(target_position, "get_target_position_side",
                               mock.Mock(return_value=trading_enums.TradeOrderSide.BUY.value)) \
                as get_target_position_side_mock:
            assert await target_position.get_target_position(mock_context, "1") == \
                   (decimal.Decimal(1), trading_enums.TradeOrderSide.BUY.value)
            parse_quantity_mock.assert_called_once_with("1")
            available_account_balance_mock.assert_called_once_with(mock_context, reduce_only=True)
            # we are at initially at 10, we want add 20% of 5 => need to buy 1.25
            get_target_position_side_mock.assert_called_once_with(decimal.Decimal("1.25"))
            adapt_amount_to_holdings_mock.assert_called_once_with(mock_context, decimal.Decimal(1.25),
                                                                  trading_enums.TradeOrderSide.BUY.value,
                                                                  False, True, False, target_price=None)
            adapt_amount_to_holdings_mock.reset_mock()
            get_target_position_side_mock.reset_mock()
            open_position_size_mock.reset_mock()

    # with negative (short) position
    with mock.patch.object(script_keywords, "adapt_amount_to_holdings",
                           mock.AsyncMock(return_value=decimal.Decimal(2))) as adapt_amount_to_holdings_mock, \
        mock.patch.object(exchange_private_data, "open_position_size",
                          mock.Mock(return_value=decimal.Decimal(-10))) as open_position_size_mock:
        with mock.patch.object(script_keywords, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.DELTA, decimal.Decimal(-3)))) \
                as parse_quantity_mock, \
             mock.patch.object(target_position, "get_target_position_side",
                               mock.Mock(return_value=trading_enums.TradeOrderSide.BUY.value)) \
                as get_target_position_side_mock:
            assert await target_position.get_target_position(mock_context, "1") == \
                   (decimal.Decimal(2), trading_enums.TradeOrderSide.BUY.value)
            parse_quantity_mock.assert_called_once_with("1")
            open_position_size_mock.assert_called_once_with(mock_context)
            get_target_position_side_mock.assert_called_once_with(decimal.Decimal(7))
            adapt_amount_to_holdings_mock.assert_called_once_with(mock_context, decimal.Decimal(7),
                                                                  trading_enums.TradeOrderSide.BUY.value,
                                                                  False, True, False, target_price=None)
            adapt_amount_to_holdings_mock.reset_mock()
            get_target_position_side_mock.reset_mock()
            open_position_size_mock.reset_mock()

        with mock.patch.object(script_keywords, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.POSITION_PERCENT, decimal.Decimal(-3)))) \
                as parse_quantity_mock, \
             mock.patch.object(target_position, "get_target_position_side",
                               mock.Mock(return_value=trading_enums.TradeOrderSide.BUY.value)) \
                as get_target_position_side_mock:
            assert await target_position.get_target_position(mock_context, "1") == \
                   (decimal.Decimal(2), trading_enums.TradeOrderSide.BUY.value)
            parse_quantity_mock.assert_called_once_with("1")
            open_position_size_mock.assert_called_once_with(mock_context)
            get_target_position_side_mock.assert_called_once_with(decimal.Decimal("10.3"))
            adapt_amount_to_holdings_mock.assert_called_once_with(mock_context, decimal.Decimal("10.3"),
                                                                  trading_enums.TradeOrderSide.BUY.value,
                                                                  False, True, False, target_price=None)
            adapt_amount_to_holdings_mock.reset_mock()
            get_target_position_side_mock.reset_mock()
            open_position_size_mock.reset_mock()
