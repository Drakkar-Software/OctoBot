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

import octobot_trading.constants
import octobot_trading.personal_data.orders.active_order_swap_strategies.stop_first_active_order_swap_strategy
import octobot_trading.personal_data.orders.active_order_swap_strategies.take_profit_first_active_order_swap_strategy

if typing.TYPE_CHECKING:
    import octobot_trading.personal_data


def create_active_order_swap_strategy(
    strategy_type: str, **kwargs
) -> "octobot_trading.personal_data.ActiveOrderSwapStrategy":
    if strategy_type == octobot_trading.personal_data.StopFirstActiveOrderSwapStrategy.__name__:
        return octobot_trading.personal_data.StopFirstActiveOrderSwapStrategy(**kwargs)
    elif strategy_type == octobot_trading.personal_data.TakeProfitFirstActiveOrderSwapStrategy.__name__:
        return octobot_trading.personal_data.TakeProfitFirstActiveOrderSwapStrategy(**kwargs)
    else:
        raise ValueError(f"Invalid active order swap strategy type: {strategy_type}")
