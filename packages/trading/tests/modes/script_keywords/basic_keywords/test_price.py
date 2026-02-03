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
import octobot_trading.modes.script_keywords.dsl as dsl
import octobot_trading.modes.script_keywords.basic_keywords.position as position
import octobot_trading.personal_data as personal_data
import octobot_trading.errors as errors
import octobot_trading.constants as constants
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc

from tests import event_loop
from tests.modes.script_keywords import null_context

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_get_price_with_offset(null_context):
    null_context.symbol = "blop/plop"
    null_context.exchange_manager = mock.Mock(
        exchange=mock.Mock(
            get_market_status=mock.Mock(return_value={
                Ecmsc.PRECISION.value: {
                    Ecmsc.PRECISION_PRICE.value: 2
                }
            })
        )
    )

    with pytest.raises(errors.InvalidArgumentError):
        await script_keywords.get_price_with_offset(null_context, "1sdsqdq")
    with pytest.raises(errors.InvalidArgumentError):
        await script_keywords.get_price_with_offset(null_context, "%")
    with pytest.raises(errors.InvalidArgumentError):
        await script_keywords.get_price_with_offset(null_context, "-%")

    with mock.patch.object(personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=200)) \
            as current_price_mock:
        with mock.patch.object(dsl, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.DELTA, decimal.Decimal(10)))) \
                as parse_quantity_mock:
            assert await script_keywords.get_price_with_offset(null_context, 10) == decimal.Decimal(210)
            current_price_mock.assert_called_once_with(
                null_context.exchange_manager, null_context.symbol, timeout=constants.ORDER_DATA_FETCHING_TIMEOUT
            )
            parse_quantity_mock.assert_called_once_with(10)
            null_context.exchange_manager.exchange.get_market_status.assert_called_once_with(
                "blop/plop", with_fixer=False
            )
            current_price_mock.reset_mock()
            parse_quantity_mock.reset_mock()

            assert await script_keywords.get_price_with_offset(null_context, 10, use_delta_type_as_flat_value=True) \
                   == decimal.Decimal(10)
            current_price_mock.assert_not_called()
            parse_quantity_mock.assert_called_once_with(10)
            current_price_mock.reset_mock()
            parse_quantity_mock.reset_mock()

        with mock.patch.object(dsl, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.DELTA_EXPLICIT, decimal.Decimal(10)))) \
                as parse_quantity_mock:
            assert await script_keywords.get_price_with_offset(null_context, 10) == decimal.Decimal(210)
            current_price_mock.assert_called_once_with(
                null_context.exchange_manager, null_context.symbol, timeout=constants.ORDER_DATA_FETCHING_TIMEOUT
            )
            parse_quantity_mock.assert_called_once_with(10)
            current_price_mock.reset_mock()
            parse_quantity_mock.reset_mock()

            # DELTA_EXPLICIT ignores use_delta_type_as_flat_value
            assert await script_keywords.get_price_with_offset(null_context, 10, use_delta_type_as_flat_value=True) \
                   == decimal.Decimal(210)
            current_price_mock.assert_called_once_with(
                null_context.exchange_manager, null_context.symbol, timeout=constants.ORDER_DATA_FETCHING_TIMEOUT
            )
            parse_quantity_mock.assert_called_once_with(10)
            current_price_mock.reset_mock()
            parse_quantity_mock.reset_mock()

        with mock.patch.object(
            dsl, "parse_quantity",
            mock.Mock(return_value=(script_keywords.QuantityType.DELTA, decimal.Decimal("10.333333")))
        ) as parse_quantity_mock:
            assert await script_keywords.get_price_with_offset(
                null_context, 10.333333, use_delta_type_as_flat_value=True
            ) == decimal.Decimal("10.33")   # rounded according to precision
            current_price_mock.assert_not_called()
            parse_quantity_mock.assert_called_once_with(10.333333)
            current_price_mock.reset_mock()
            parse_quantity_mock.reset_mock()

        with mock.patch.object(dsl, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.PERCENT, decimal.Decimal(-99)))):
            assert await script_keywords.get_price_with_offset(null_context, 10) == decimal.Decimal(2)

        with mock.patch.object(dsl, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.PERCENT, decimal.Decimal(1000)))):
            assert await script_keywords.get_price_with_offset(null_context, 10) == decimal.Decimal(2200)

    with mock.patch.object(position, "average_open_pos_entry", mock.AsyncMock(return_value=500)) \
            as average_open_pos_entry_mock:
        with mock.patch.object(dsl, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.ENTRY_PERCENT, decimal.Decimal(-50)))):
            assert await script_keywords.get_price_with_offset(null_context, 10, side="sell") == decimal.Decimal(250)
            average_open_pos_entry_mock.assert_called_once_with(null_context, "sell")

    with mock.patch.object(position, "average_open_pos_entry", mock.AsyncMock(return_value=500)) \
            as average_open_pos_entry_mock:
        with mock.patch.object(dsl, "parse_quantity",
                               mock.Mock(return_value=(script_keywords.QuantityType.ENTRY, decimal.Decimal(50)))):
            assert await script_keywords.get_price_with_offset(null_context, 10, side="sell") == decimal.Decimal(550)
            average_open_pos_entry_mock.assert_called_once()

    with mock.patch.object(dsl, "parse_quantity",
                           mock.Mock(return_value=(script_keywords.QuantityType.FLAT, decimal.Decimal(50)))):
        assert await script_keywords.get_price_with_offset(null_context, 10) == decimal.Decimal(50)

    with mock.patch.object(dsl, "parse_quantity",
                           mock.Mock(return_value=(script_keywords.QuantityType.DELTA_QUOTE, decimal.Decimal(50)))):
        assert await script_keywords.get_price_with_offset(null_context, 10) == decimal.Decimal(50)

    with mock.patch.object(dsl, "parse_quantity",
                           mock.Mock(return_value=(script_keywords.QuantityType.UNKNOWN, decimal.Decimal(-50)))):
        with pytest.raises(errors.InvalidArgumentError):
            await script_keywords.get_price_with_offset(null_context, 10)
