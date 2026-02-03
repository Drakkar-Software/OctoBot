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
import typing
import decimal

import octobot_trading.errors
import octobot_trading.personal_data.orders.groups.balanced_take_profit_and_stop_order_group as \
    balanced_take_profit_and_stop_order_group
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.personal_data.orders.order as order_import
import octobot_trading.personal_data.orders.trailing_profiles as trailing_profiles_import

import octobot_trading.constants as constants


class TrailingOnFilledTPBalancedOrderGroup(
    balanced_take_profit_and_stop_order_group.BalancedTakeProfitAndStopOrderGroup
):
    """
    TrailingOnFilledTPBalancedOrderGroup is a BalancedTakeProfitAndStopOrderGroup that also applies a trailing
    profile to stop losses
    """

    def _balances_factory(self, closed_order, filled):
        return {
            self.TAKE_PROFIT: balanced_take_profit_and_stop_order_group.SideBalance(closed_order, filled),
            self.STOP: TrailingSideBalance(closed_order, filled)  # only stop orders are trailing
        }

    @classmethod
    def _get_reversed_order_update(cls, order_update: dict, included_fields: list) -> dict:
        reversed_update = super()._get_reversed_order_update(order_update, included_fields)
        reversed_update[cls.UPDATED_PRICE] = (
            order_update[cls.INITIAL_PRICE] if cls.UPDATED_PRICE in included_fields else None
        )
        return reversed_update


class TrailingSideBalance(balanced_take_profit_and_stop_order_group.SideBalance):
    def _get_relevant_price(self, order: order_import.Order) -> decimal.Decimal:
        filled_price = self.closed_order.origin_price if self.closed_order and self.are_closed_orders_filled else None
        current_price, up_to_date = order_util.get_potentially_outdated_price(order.exchange_manager, order.symbol)
        if not up_to_date:
            self.get_logger().warning(
                f"{order.exchange_manager.exchange_name} mark price: {current_price} is outdated for {order.symbol}. "
                f"Using it anyway."
            )
        if filled_price is None or filled_price == constants.ZERO:
            return current_price
        if order.trigger_above:
            # trigger above means it's a SL in a short position: price will trail down, look for min price
            return min(filled_price, current_price)
        # it's a SL in a long position: trail up and use max price as reference
        return max(filled_price, current_price)

    def _get_next_trailing_price(self, order: order_import.Order) -> typing.Optional[decimal.Decimal]:
        if not isinstance(order.trailing_profile, trailing_profiles_import.FilledTakeProfitTrailingProfile):
            self.get_logger().error(f"Ignored trailing profile: {order.trailing_profile} for order {order}")
            return None
        try:
            updated_price = self._get_relevant_price(order)
            return order.trailing_profile.update_and_get_trailing_price(updated_price)
        except octobot_trading.errors.ExhaustedTrailingProfileError as err:
            self.get_logger().error(f"Impossible to compute next trailing price: {err}")
        return None

    def get_order_update(self, order, updated_quantity: typing.Optional[decimal.Decimal]) -> dict:
        # order should be updated, meaning it's quantity will be adjusted (from parent class SideBalance).
        # here we also want to update its price according to the trailing profile
        base_update = super().get_order_update(order, updated_quantity)
        base_update[TrailingOnFilledTPBalancedOrderGroup.UPDATED_PRICE] = self._get_next_trailing_price(order)
        base_update[TrailingOnFilledTPBalancedOrderGroup.INITIAL_PRICE] = order.origin_price
        return base_update
