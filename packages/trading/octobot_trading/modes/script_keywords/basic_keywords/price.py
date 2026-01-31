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
import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.personal_data as personal_data
import octobot_trading.modes.script_keywords.dsl as dsl
import octobot_trading.modes.script_keywords.basic_keywords.position as position


async def get_price_with_offset(context, offset_input, use_delta_type_as_flat_value=False, side=None):
    if offset_input is None:
        raise errors.InvalidArgumentError("price or offset is required")
    offset_type, offset_value = dsl.parse_quantity(offset_input)

    if offset_value is None:
        raise errors.InvalidArgumentError(f"Invalid price: parsed value can't be None (input: {offset_input})")

    # when use_delta_type_as_flat_value is True, consider a simple price input as a flat target instead of an offset
    is_delta_type_considered_as_flat = offset_type is dsl.QuantityType.DELTA and use_delta_type_as_flat_value

    if offset_type is dsl.QuantityType.DELTA_EXPLICIT or (
        offset_type is dsl.QuantityType.DELTA and not is_delta_type_considered_as_flat
    ):
        current_price_val = await personal_data.get_up_to_date_price(
            context.exchange_manager, context.symbol, timeout=constants.ORDER_DATA_FETCHING_TIMEOUT
        )
        # offset should be negative when wanting to buy bellow current price
        computed_price = current_price_val + offset_value

    elif offset_type is dsl.QuantityType.PERCENT:
        current_price_val = await personal_data.get_up_to_date_price(
            context.exchange_manager, context.symbol, timeout=constants.ORDER_DATA_FETCHING_TIMEOUT
        )
        computed_price = current_price_val * (constants.ONE + (offset_value / constants.ONE_HUNDRED))

    elif offset_type is dsl.QuantityType.ENTRY_PERCENT:
        average_open_pos_entry_val = await position.average_open_pos_entry(context, side)
        computed_price = average_open_pos_entry_val * (constants.ONE + (offset_value / constants.ONE_HUNDRED))

    elif offset_type is dsl.QuantityType.ENTRY:
        average_open_pos_entry_val = await position.average_open_pos_entry(context, side)
        computed_price = average_open_pos_entry_val + offset_value

    elif is_delta_type_considered_as_flat or offset_type in (dsl.QuantityType.FLAT, dsl.QuantityType.DELTA_QUOTE):
        computed_price = offset_value
    else:
        raise errors.InvalidArgumentError(
            f"'{offset_input}' is not supported. "
            f"Make sure to use a supported syntax for price, supported parameters are: "
            f"1.2, -0.222, -0.222d, @65100, 5%, e5%, e500"
        )

    symbol_market = context.exchange_manager.exchange.get_market_status(context.symbol, with_fixer=False)
    return personal_data.decimal_adapt_price(symbol_market, computed_price)
