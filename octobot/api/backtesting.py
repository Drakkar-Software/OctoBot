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
import octobot.backtesting as backtesting
import octobot_backtesting.constants as constants


def create_independent_backtesting(config,
                                   tentacles_setup_config,
                                   data_files,
                                   data_file_path=constants.BACKTESTING_FILE_PATH,
                                   join_backtesting_timeout=constants.BACKTESTING_DEFAULT_JOIN_TIMEOUT,
                                   run_on_common_part_only=True) -> backtesting.IndependentBacktesting:
    return backtesting.IndependentBacktesting(config, tentacles_setup_config, data_files,
                                              data_file_path,
                                              run_on_common_part_only=run_on_common_part_only,
                                              join_backtesting_timeout=join_backtesting_timeout)


async def initialize_and_run_independent_backtesting(independent_backtesting, log_errors=True) -> None:
    await independent_backtesting.initialize_and_run(log_errors=log_errors)


async def join_independent_backtesting(independent_backtesting, timeout=constants.BACKTESTING_DEFAULT_JOIN_TIMEOUT) -> None:
    await independent_backtesting.join_backtesting_updater(timeout)


async def initialize_independent_backtesting_config(independent_backtesting) -> dict:
    return await independent_backtesting.initialize_config()


async def stop_independent_backtesting(independent_backtesting, memory_check=False, should_raise=False) -> None:
    await independent_backtesting.stop(memory_check=memory_check, should_raise=should_raise)


def check_independent_backtesting_remaining_objects(independent_backtesting) -> None:
    independent_backtesting.octobot_backtesting.check_remaining_objects()


def is_independent_backtesting_in_progress(independent_backtesting) -> bool:
    return independent_backtesting.is_in_progress()


def is_independent_backtesting_computing(independent_backtesting) -> bool:
    return independent_backtesting.is_in_progress()


def get_independent_backtesting_progress(independent_backtesting) -> float:
    return independent_backtesting.get_progress()


def is_independent_backtesting_finished(independent_backtesting) -> bool:
    return independent_backtesting.get_progress() == 1.0


def is_independent_backtesting_stopped(independent_backtesting) -> bool:
    return independent_backtesting.stopped


async def get_independent_backtesting_report(independent_backtesting) -> dict:
    return await independent_backtesting.get_dict_formatted_report()


def get_independent_backtesting_exchange_manager_ids(independent_backtesting) -> list:
    return independent_backtesting.octobot_backtesting.exchange_manager_ids


def log_independent_backtesting_report(independent_backtesting) -> None:
    independent_backtesting.log_report()
