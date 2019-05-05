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

from copy import copy


from tools.logging.logging_util import get_logger
from backtesting.collector.data_file_manager import get_all_available_data_files, get_file_description, delete_data_file
from backtesting.backtester import Backtester
from backtesting.collector.data_collector import DataCollector
from interfaces import get_bot
from config import BOT_TOOLS_STRATEGY_OPTIMIZER, BOT_TOOLS_BACKTESTING, CONFIG_DATA_COLLECTOR_PATH


LOGGER = get_logger("DataCollectorWebInterfaceModel")


def get_data_files_with_description():
    files = get_all_available_data_files()
    files_with_description = {
        data_file: get_file_description(data_file) for data_file in files
    }
    return files_with_description


def start_backtesting_using_specific_files(files, source, reset_tentacle_config=False):
    try:
        tools = get_bot().get_tools()
        if tools[BOT_TOOLS_STRATEGY_OPTIMIZER] and tools[BOT_TOOLS_STRATEGY_OPTIMIZER].get_is_computing():
            return False, "Optimizer already running"
        elif tools[BOT_TOOLS_BACKTESTING] and tools[BOT_TOOLS_BACKTESTING].get_is_computing():
            return False, "A backtesting is already running"
        else:
            backtester = Backtester(get_bot().get_config(), source, files, reset_tentacle_config=reset_tentacle_config)
            tools[BOT_TOOLS_BACKTESTING] = backtester
            if get_bot().run_in_main_asyncio_loop(backtester.start_backtesting(in_thread=True)):
                ignored_files = backtester.get_ignored_files()
                ignored_files_info = "" if not ignored_files else f" ignored files: {ignored_files}"
                return True, f"Backtesting started{ignored_files_info}"
            else:
                return False, "Impossible to start backtesting"
    except Exception as e:
        LOGGER.exception(e)
        return False, f"Error when starting backtesting: {e}"


def get_backtesting_status():
    tools = get_bot().get_tools()
    if tools[BOT_TOOLS_BACKTESTING]:
        backtester = tools[BOT_TOOLS_BACKTESTING]
        if backtester.get_is_computing():
            return "computing", backtester.get_progress()
        return "finished", 100
    else:
        return "not started", 0


def get_backtesting_report(source):
    tools = get_bot().get_tools()
    if tools[BOT_TOOLS_BACKTESTING]:
        backtester = tools[BOT_TOOLS_BACKTESTING]
        if backtester.get_finished_source() == source:
            return get_bot().run_in_main_asyncio_loop(backtester.get_report())
    return {}


def get_delete_data_file(file_name):
    deleted, error = delete_data_file(file_name)
    if deleted:
        return deleted, f"{file_name} deleted"
    else:
        return deleted, f"Can't delete {file_name} ({error})"


def collect_data_file(exchange, symbol):
    success = False
    data_collector = DataCollector(copy(get_bot().get_config()), False)

    try:
        result = get_bot().run_in_main_asyncio_loop(data_collector.execute_with_specific_target(exchange, symbol))
        success = True
    except Exception as e:
        data_collector.stop()
        result = f"data collector error: {e}"

    if success:
        return success, f"{result} saved"
    else:
        return success, f"Can't collect data for {symbol} on {exchange} ({result})"


def save_data_file(name, file):
    try:
        file.save(CONFIG_DATA_COLLECTOR_PATH+name)
        message = f"{name} saved"
        LOGGER.info(message)
        return True, message
    except Exception as e:
        message = f"Error when saving file: {e}. File can't be saved."
        LOGGER.error(message)
        return False, message
