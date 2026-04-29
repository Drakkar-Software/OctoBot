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
import octobot_trading.personal_data.orders.cancel_policies.order_cancel_policy as order_cancel_policy_import
import octobot_trading.personal_data.orders.cancel_policies.expiration_time_order_cancel_policy as expiration_time_order_cancel_policy_import
import octobot_trading.personal_data.orders.cancel_policies.chained_order_filling_price_order_cancel_policy as chained_order_filling_price_order_cancel_policy_import
import octobot_trading.errors as errors



def create_cancel_policy(
    policy_class_name: str,
    kwargs: typing.Optional[dict] = None
) -> order_cancel_policy_import.OrderCancelPolicy:
    """
    Create a cancel policy instance from its class name and kwargs.
    
    :param policy_class_name: The name of the cancel policy class
    :param kwargs: Optional dictionary of keyword arguments to pass to the policy constructor
    :return: An instance of the cancel policy, or None if the class name is not recognized
    """
    kwargs = kwargs or {}
    try:
        if policy_class_name == expiration_time_order_cancel_policy_import.ExpirationTimeOrderCancelPolicy.__name__:
            return expiration_time_order_cancel_policy_import.ExpirationTimeOrderCancelPolicy(**kwargs)
        elif policy_class_name == chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy.__name__:
            return chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy(**kwargs)
    except TypeError as err:
        raise errors.InvalidCancelPolicyError(f"Invalid kwargs for {policy_class_name}: {err}") from err
    raise NotImplementedError(f"Unsupported cancel policy class name: {policy_class_name}")
