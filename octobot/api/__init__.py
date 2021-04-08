#  Drakkar-Software OctoBot
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

from octobot.api import backtesting
from octobot.api import strategy_optimizer
from octobot.api import updater

from octobot.api.backtesting import (
    create_independent_backtesting,
    check_independent_backtesting_remaining_objects,
    is_independent_backtesting_in_progress,
    is_independent_backtesting_computing,
    get_independent_backtesting_progress,
    is_independent_backtesting_finished,
    is_independent_backtesting_stopped,
    get_independent_backtesting_exchange_manager_ids,
    log_independent_backtesting_report,
    initialize_and_run_independent_backtesting,
    join_independent_backtesting,
    initialize_independent_backtesting_config,
    stop_independent_backtesting,
    get_independent_backtesting_report,
)
from octobot.api.strategy_optimizer import (
    create_strategy_optimizer,
    find_optimal_configuration,
    print_optimizer_report,
    get_optimizer_report,
    get_optimizer_results,
    get_optimizer_overall_progress,
    is_optimizer_in_progress,
    is_optimizer_computing,
    get_optimizer_errors_description,
    get_optimizer_current_test_suite_progress,
    get_optimizer_strategy,
    get_optimizer_all_time_frames,
    get_optimizer_all_TAs,
    get_optimizer_all_risks,
    get_optimizer_trading_mode,
    get_optimizer_is_properly_initialized,
)
from octobot.api.updater import (
    get_updater,
)

__all__ = [
    "create_independent_backtesting",
    "check_independent_backtesting_remaining_objects",
    "is_independent_backtesting_in_progress",
    "is_independent_backtesting_computing",
    "get_independent_backtesting_progress",
    "is_independent_backtesting_finished",
    "is_independent_backtesting_stopped",
    "get_independent_backtesting_exchange_manager_ids",
    "log_independent_backtesting_report",
    "initialize_and_run_independent_backtesting",
    "join_independent_backtesting",
    "initialize_independent_backtesting_config",
    "stop_independent_backtesting",
    "get_independent_backtesting_report",
    "create_strategy_optimizer",
    "find_optimal_configuration",
    "print_optimizer_report",
    "get_optimizer_report",
    "get_optimizer_results",
    "get_optimizer_overall_progress",
    "is_optimizer_in_progress",
    "is_optimizer_computing",
    "get_optimizer_errors_description",
    "get_optimizer_current_test_suite_progress",
    "get_optimizer_strategy",
    "get_optimizer_all_time_frames",
    "get_optimizer_all_TAs",
    "get_optimizer_all_risks",
    "get_optimizer_trading_mode",
    "get_optimizer_is_properly_initialized",
    "get_updater",
]
