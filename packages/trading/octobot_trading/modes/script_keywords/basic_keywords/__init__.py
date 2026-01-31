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

from octobot_trading.modes.script_keywords.basic_keywords.user_inputs import (
    user_input,
    save_user_input,
    get_activation_topics,
)

from octobot_commons.configuration import (
    get_user_inputs,
    clear_user_inputs,
)

from octobot_trading.modes.script_keywords.basic_keywords.configuration import (
    user_select_leverage,
    user_select_emit_trading_signals,
    set_leverage,
    set_partial_take_profit_stop_loss,
)

from octobot_trading.modes.script_keywords.basic_keywords.amount import (
    get_amount_from_input_amount,
)

from octobot_trading.modes.script_keywords.basic_keywords.price import (
    get_price_with_offset,
)

from octobot_trading.modes.script_keywords.basic_keywords.position import (
    get_position,
    average_open_pos_entry,
    is_in_one_way_position_mode,
)

from octobot_trading.modes.script_keywords.basic_keywords.account_balance import (
    total_account_balance,
    available_account_balance,
    adapt_amount_to_holdings,
    account_holdings,
    get_order_size_portfolio_percent,
)

from octobot_trading.modes.script_keywords.basic_keywords.trading_signals import (
    is_emitting_trading_signals,
    emit_trading_signals,
)


from octobot_trading.modes.script_keywords.basic_keywords.run_persistence import (
    disable_candles_plot,
    set_plot_orders,
    clear_orders_cache,
    clear_symbol_plot_cache,
)


__all__ = [
    "user_input",
    "save_user_input",
    "get_user_inputs",
    "clear_user_inputs",
    "get_activation_topics",
    "user_select_leverage",
    "user_select_emit_trading_signals",
    "is_emitting_trading_signals",
    "emit_trading_signals",
    "set_leverage",
    "set_partial_take_profit_stop_loss",
    "get_amount_from_input_amount",
    "get_price_with_offset",
    "get_position",
    "average_open_pos_entry",
    "is_in_one_way_position_mode",
    "total_account_balance",
    "available_account_balance",
    "adapt_amount_to_holdings",
    "account_holdings",
    "get_order_size_portfolio_percent",
    "disable_candles_plot",
    "set_plot_orders",
    "clear_orders_cache",
    "clear_symbol_plot_cache",
]
