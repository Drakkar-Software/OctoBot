#  Drakkar-Software OctoBot-Services
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

from octobot_services.interfaces import abstract_interface
from octobot_services.interfaces.abstract_interface import (
    AbstractInterface,
)

from octobot_services.interfaces import interface_factory
from octobot_services.interfaces import bots
from octobot_services.interfaces import util
from octobot_services.interfaces import web

from octobot_services.interfaces.interface_factory import (
    InterfaceFactory,
)
from octobot_services.interfaces.bots import (
    AbstractBotInterface,
    LOGGER,
    EOL,
    NO_TRADER_MESSAGE,
    NO_CURRENCIES_MESSAGE,
)
from octobot_services.interfaces.util import (
    get_bot_api,
    get_exchange_manager_ids,
    get_global_config,
    get_startup_config,
    get_edited_config,
    get_startup_tentacles_config,
    get_edited_tentacles_config,
    get_exchange_managers,
    run_in_bot_main_loop,
    run_in_bot_async_executor,
    get_all_open_orders,
    cancel_orders,
    cancel_all_open_orders,
    async_cancel_orders,
    async_cancel_all_open_orders,
    has_trader,
    has_real_and_or_simulated_traders,
    sell_all_currencies,
    sell_all,
    async_sell_all_currencies,
    async_sell_all,
    set_enable_trading,
    get_total_paid_fees,
    get_trades_history,
    set_risk,
    get_risk,
    get_currencies_with_status,
    get_matrix_list,
    get_portfolio_holdings,
    get_portfolio_current_value,
    get_global_portfolio_currencies_amounts,
    get_global_portfolio_currencies_values,
    trigger_portfolios_refresh,
    async_trigger_portfolios_refresh,
    get_global_profitability,
    get_reference_market,
    get_all_positions,
    close_positions,
    async_close_positions,
)
from octobot_services.interfaces.web import (
    AbstractWebInterface,
)

__all__ = [
    "AbstractInterface",
    "InterfaceFactory",
    "AbstractWebInterface",
    "get_bot_api",
    "get_exchange_manager_ids",
    "get_global_config",
    "get_startup_config",
    "get_edited_config",
    "get_startup_tentacles_config",
    "get_edited_tentacles_config",
    "get_exchange_managers",
    "run_in_bot_main_loop",
    "run_in_bot_async_executor",
    "get_all_open_orders",
    "cancel_orders",
    "cancel_all_open_orders",
    "async_cancel_orders",
    "async_cancel_all_open_orders",
    "has_trader",
    "has_real_and_or_simulated_traders",
    "sell_all_currencies",
    "sell_all",
    "async_sell_all_currencies",
    "async_sell_all",
    "set_enable_trading",
    "get_total_paid_fees",
    "get_trades_history",
    "set_risk",
    "get_risk",
    "get_currencies_with_status",
    "get_matrix_list",
    "get_portfolio_holdings",
    "get_portfolio_current_value",
    "get_global_portfolio_currencies_amounts",
    "get_global_portfolio_currencies_values",
    "trigger_portfolios_refresh",
    "async_trigger_portfolios_refresh",
    "get_global_profitability",
    "get_reference_market",
    "AbstractBotInterface",
    "LOGGER",
    "EOL",
    "NO_TRADER_MESSAGE",
    "NO_CURRENCIES_MESSAGE",
    "get_all_positions",
    "close_positions",
    "async_close_positions",
]
