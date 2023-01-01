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
import octobot.backtesting as backtesting
import octobot_backtesting.constants as constants


def create_independent_backtesting(config,
                                   tentacles_setup_config,
                                   data_files,
                                   data_file_path=constants.BACKTESTING_FILE_PATH,
                                   join_backtesting_timeout=constants.BACKTESTING_DEFAULT_JOIN_TIMEOUT,
                                   run_on_common_part_only=True,
                                   start_timestamp=None,
                                   end_timestamp=None,
                                   enable_logs=True,
                                   stop_when_finished=False,
                                   enforce_total_databases_max_size_after_run=True,
                                   enable_storage=True,
                                   run_on_all_available_time_frames=False,
                                   backtesting_data=None) \
        -> backtesting.IndependentBacktesting:
    return backtesting.IndependentBacktesting(
        config, tentacles_setup_config, data_files,
        data_file_path,
        run_on_common_part_only=run_on_common_part_only,
        join_backtesting_timeout=join_backtesting_timeout,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        enable_logs=enable_logs,
        stop_when_finished=stop_when_finished,
        enforce_total_databases_max_size_after_run=enforce_total_databases_max_size_after_run,
        enable_storage=enable_storage,
        run_on_all_available_time_frames=run_on_all_available_time_frames,
        backtesting_data=backtesting_data,
    )


async def initialize_and_run_independent_backtesting(independent_backtesting, log_errors=True) -> None:
    await independent_backtesting.initialize_and_run(log_errors=log_errors)


async def join_independent_backtesting(independent_backtesting, timeout=constants.BACKTESTING_DEFAULT_JOIN_TIMEOUT) -> None:
    await independent_backtesting.join_backtesting_updater(timeout)


async def initialize_independent_backtesting_config(independent_backtesting) -> dict:
    return await independent_backtesting.initialize_config()


async def stop_independent_backtesting(independent_backtesting, memory_check=False, should_raise=False) -> None:
    await independent_backtesting.stop(memory_check=memory_check, should_raise=should_raise)


async def join_independent_backtesting_stop(independent_backtesting, timeout=None):
    await independent_backtesting.join_stop_event(timeout=timeout)


def check_independent_backtesting_remaining_objects(independent_backtesting) -> None:
    independent_backtesting.octobot_backtesting.check_remaining_objects()


def is_independent_backtesting_in_progress(independent_backtesting) -> bool:
    return independent_backtesting.is_in_progress()


def is_independent_backtesting_computing(independent_backtesting) -> bool:
    return independent_backtesting.is_in_progress()


def get_independent_backtesting_progress(independent_backtesting) -> float:
    return independent_backtesting.get_progress()


def is_independent_backtesting_finished(independent_backtesting) -> bool:
    return independent_backtesting.has_finished()


def is_independent_backtesting_stopped(independent_backtesting) -> bool:
    return independent_backtesting.stopped


async def get_independent_backtesting_report(independent_backtesting) -> dict:
    return await independent_backtesting.get_dict_formatted_report()


def get_independent_backtesting_exchange_manager_ids(independent_backtesting) -> list:
    return independent_backtesting.octobot_backtesting.exchange_manager_ids


def get_independent_backtesting_bot_id(independent_backtesting) -> str:
    return independent_backtesting.octobot_backtesting.bot_id


def log_independent_backtesting_report(independent_backtesting) -> None:
    independent_backtesting.log_report()


def get_independent_backtesting_config(independent_backtesting) -> dict:
    return independent_backtesting.octobot_backtesting.backtesting_config


def get_independent_backtesting_symbols_by_exchanges(independent_backtesting) -> dict:
    return independent_backtesting.octobot_backtesting.symbols_to_create_exchange_classes
