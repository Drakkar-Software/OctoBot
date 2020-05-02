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
from octobot.strategy_optimizer.strategy_optimizer import StrategyOptimizer


def create_strategy_optimizer(config, tentacles_setup_config, strategy_name) -> StrategyOptimizer:
    return StrategyOptimizer(config, tentacles_setup_config, strategy_name)


def find_optimal_configuration(strategy_optimizer, TAs=None, time_frames=None, risks=None) -> None:
    strategy_optimizer.find_optimal_configuration(TAs=TAs, time_frames=time_frames, risks=risks)


def print_optimizer_report(strategy_optimizer) -> None:
    strategy_optimizer.print_report()


def get_optimizer_report(strategy_optimizer) -> list:
    return strategy_optimizer.get_report()


def get_optimizer_results(strategy_optimizer) -> list:
    return strategy_optimizer.run_results


def get_optimizer_overall_progress(strategy_optimizer) -> int:
    return strategy_optimizer.get_overall_progress()


def is_optimizer_in_progress(strategy_optimizer) -> bool:
    return strategy_optimizer.is_in_progress()


def is_optimizer_computing(strategy_optimizer) -> bool:
    return strategy_optimizer.is_computing


def get_optimizer_errors_description(strategy_optimizer) -> str:
    return strategy_optimizer.get_errors_description()


def get_optimizer_current_test_suite_progress(strategy_optimizer) -> int:
    return strategy_optimizer.get_current_test_suite_progress()


def get_optimizer_strategy(strategy_optimizer) -> object:
    return strategy_optimizer.strategy_class


def get_optimizer_all_time_frames(strategy_optimizer) -> list:
    return strategy_optimizer.all_time_frames


def get_optimizer_all_TAs(strategy_optimizer) -> list:
    return strategy_optimizer.all_TAs


def get_optimizer_all_risks(strategy_optimizer) -> list:
    return strategy_optimizer.risks


def get_optimizer_trading_mode(strategy_optimizer) -> object:
    return strategy_optimizer.trading_mode


def get_optimizer_is_properly_initialized(strategy_optimizer) -> bool:
    return strategy_optimizer.is_properly_initialized
