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
import decimal

import octobot_trading.personal_data.orders.trailing_profiles.trailing_profile as trailing_profile
import octobot_trading.personal_data.orders.trailing_profiles.trailing_profile_types as trailing_profile_types
import octobot_trading.personal_data.orders.trailing_profiles.trailing_price_step as trailing_price_step
import octobot_trading.personal_data.orders.trailing_profiles.filled_take_profit_trailing_profile as \
    filled_take_profit_trailing_profile


def create_trailing_profile(
    profile_type: trailing_profile_types.TrailingProfileTypes,
    profile: dict
) -> trailing_profile.TrailingProfile:
    if profile_type == filled_take_profit_trailing_profile.FilledTakeProfitTrailingProfile.get_type():
        return filled_take_profit_trailing_profile.FilledTakeProfitTrailingProfile.from_dict(profile)
    raise NotImplementedError(f"Unsupported profile_type: {profile_type}")


def create_filled_take_profit_trailing_profile(
    entry_price: decimal.Decimal, take_profit_orders: list
) -> filled_take_profit_trailing_profile.FilledTakeProfitTrailingProfile:
    if not take_profit_orders:
        raise ValueError(f"take_profit_orders can't be empty")
    previous_order = take_profit_orders[0]
    trigger_above = previous_order.trigger_above
    steps = [
        trailing_price_step.TrailingPriceStep(
            float(entry_price), float(previous_order.origin_price), trigger_above
        )
    ]
    for order in take_profit_orders[1:]:
        if order.trigger_above != trigger_above:
            raise ValueError(
                f"trigger_above can't be different from first given order trigger_above value: {trigger_above}"
            )
        steps.append(
            trailing_price_step.TrailingPriceStep(
                # trailing price is the origin price of the previous order
                float(previous_order.origin_price), float(order.origin_price), order.trigger_above
            )
        )
        previous_order = order
    return filled_take_profit_trailing_profile.FilledTakeProfitTrailingProfile(steps)