#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import octobot.strategy_optimizer.strategy_optimizer as strategy_optimizer
import octobot.strategy_optimizer.strategy_design_optimizer as strategy_design_optimizer
import octobot.strategy_optimizer.optimizer_settings as optimizer_settings_import
import octobot.strategy_optimizer.strategy_design_optimizer_factory as strategy_design_optimizer_factory


def create_strategy_optimizer(config, tentacles_setup_config, strategy_name) -> strategy_optimizer.StrategyOptimizer:
    return strategy_optimizer.StrategyOptimizer(config, tentacles_setup_config, strategy_name)


def create_design_strategy_optimizer(
        trading_mode, optimizer_settings, config=None, tentacles_setup_config=None
) -> strategy_design_optimizer.StrategyDesignOptimizer:
    return strategy_design_optimizer_factory.create_most_advanced_strategy_design_optimizer(
        trading_mode, config, tentacles_setup_config, optimizer_settings=optimizer_settings
    )


async def initialize_design_strategy_optimizer(strategy_optimizer, is_resuming, is_computing=False):
    strategy_optimizer.is_computing = is_computing
    return await strategy_optimizer.initialize(is_resuming)


async def update_strategy_optimizer_total_runs(optimizer, runs):
    if optimizer.empty_the_queue:
        optimizer.total_nb_runs += len(runs)


async def generate_and_save_strategy_optimizer_runs(trading_mode, tentacles_setup_config, optimizer_settings) -> list:
    optimizer = create_design_strategy_optimizer(trading_mode, optimizer_settings, None, tentacles_setup_config)
    return await optimizer.generate_and_save_run()


def create_strategy_optimizer_settings(settings_dict: dict) -> optimizer_settings_import.OptimizerSettings:
    return optimizer_settings_import.OptimizerSettings(settings_dict)


async def resume_design_strategy_optimizer(optimizer, optimizer_settings: optimizer_settings_import.OptimizerSettings):
    # continue till the queue is empty if no optimizer id is specified
    optimizer_settings.empty_the_queue = optimizer_settings.optimizer_ids is None
    optimizer_settings.optimizer_ids = optimizer_settings.optimizer_ids or await optimizer.get_queued_optimizer_ids()
    return await optimizer.resume(optimizer_settings)


def find_optimal_configuration(strategy_optimizer, TAs=None, time_frames=None, risks=None) -> None:
    strategy_optimizer.find_optimal_configuration(TAs=TAs, time_frames=time_frames, risks=risks)


def cancel_strategy_optimizer(strategy_optimizer):
    strategy_optimizer.cancel()


def print_optimizer_report(strategy_optimizer) -> None:
    strategy_optimizer.print_report()


def get_optimizer_report(strategy_optimizer) -> list:
    return strategy_optimizer.get_report()


def get_optimizer_results(strategy_optimizer) -> list:
    return strategy_optimizer.run_results


async def get_optimizer_overall_progress(strategy_optimizer) -> (int, float):
    return await strategy_optimizer.get_overall_progress()


async def get_design_strategy_optimizer_queue(trading_mode) -> list:
    return await strategy_design_optimizer.StrategyDesignOptimizer.get_run_queue(trading_mode)


async def update_design_strategy_optimizer_queue(trading_mode, updated_queue) -> list:
    return await strategy_design_optimizer.StrategyDesignOptimizer.update_run_queue(trading_mode, updated_queue)


async def is_optimizer_in_progress(strategy_optimizer) -> bool:
    return await strategy_optimizer.is_in_progress()


def is_optimizer_computing(strategy_optimizer) -> bool:
    return strategy_optimizer.is_computing


def is_optimizer_finished(strategy_optimizer) -> bool:
    return strategy_optimizer.is_finished


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
