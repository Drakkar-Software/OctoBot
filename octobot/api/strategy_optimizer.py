#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
from octobot.strategy_optimizer.strategy_optimizer import StrategyOptimizer
from octobot.strategy_optimizer.strategy_design_optimizer import StrategyDesignOptimizer


def create_strategy_optimizer(config, tentacles_setup_config, strategy_name) -> StrategyOptimizer:
    return StrategyOptimizer(config, tentacles_setup_config, strategy_name)


def create_design_strategy_optimizer(trading_mode, config=None, tentacles_setup_config=None,
                                     optimizer_config=None) -> StrategyDesignOptimizer:
    return StrategyDesignOptimizer(trading_mode, config, tentacles_setup_config, optimizer_config)


async def initialize_design_strategy_optimizer(strategy_optimizer, is_resuming, is_computing=False):
    strategy_optimizer.is_computing = is_computing
    return await strategy_optimizer.initialize(is_resuming)


async def update_strategy_optimizer_total_runs(optimizer, runs):
    if optimizer.empty_the_queue:
        optimizer.total_nb_runs += len(runs)


async def generate_and_save_strategy_optimizer_runs(trading_mode, tentacles_setup_config,
                                                    optimizer_config, optimizer_id, queue_size) -> list:
    optimizer = StrategyDesignOptimizer(trading_mode, None, tentacles_setup_config,
                                        optimizer_config, optimizer_id, queue_size)
    return await optimizer.generate_and_save_run()


async def resume_design_strategy_optimizer(optimizer, data_files, randomly_chose_runs, start_timestamp, end_timestamp,
                                           required_idle_cores, notify_when_complete=False, optimizer_ids=None):
    empty_the_queue = optimizer_ids is None  # continue till the queue is empty if no optimizer id is specified
    optimizer_ids = optimizer_ids or await optimizer.get_queued_optimizer_ids()
    return await optimizer.resume(data_files, optimizer_ids, randomly_chose_runs,
                                  start_timestamp=start_timestamp,
                                  end_timestamp=end_timestamp,
                                  empty_the_queue=empty_the_queue,
                                  required_idle_cores=required_idle_cores,
                                  notify_when_complete=notify_when_complete)


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
    return await StrategyDesignOptimizer.get_run_queue(trading_mode)


async def update_design_strategy_optimizer_queue(trading_mode, updated_queue) -> list:
    return await StrategyDesignOptimizer.update_run_queue(trading_mode, updated_queue)


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
