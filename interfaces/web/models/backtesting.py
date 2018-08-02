from backtesting.collector.data_file_manager import get_all_available_data_files, get_file_description
from backtesting.backtester import Backtester
from tests.test_utils.backtesting_util import get_standalone_backtesting_bot, start_backtesting_bot
from interfaces import get_bot
from config.cst import BOT_TOOLS_STRATEGY_OPTIMIZER, BOT_TOOLS_BACKTESTING


def get_data_files_with_description():
    files = get_all_available_data_files()
    files_with_description = {
        file: get_file_description(file) for file in files
    }
    return files_with_description


def start_backtesting_using_files(files):
    try:
        tools = get_bot().get_tools()
        if tools[BOT_TOOLS_STRATEGY_OPTIMIZER] and tools[BOT_TOOLS_STRATEGY_OPTIMIZER].get_is_computing():
            return False, "Optimizer already running"
        elif tools[BOT_TOOLS_BACKTESTING] and tools[BOT_TOOLS_BACKTESTING].get_is_computing():
            return False, "A backtesting is already running"
        else:
            bot, ignored_files = get_standalone_backtesting_bot(get_bot().get_config(), files)
            tools[BOT_TOOLS_BACKTESTING] = Backtester(bot)
            if start_backtesting_bot(bot, in_thread=True):
                return True, "Backtesting started"
            else:
                return False, "Impossible to start backtesting"
    except Exception as e:
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


def get_backtesting_report():
    tools = get_bot().get_tools()
    if tools[BOT_TOOLS_BACKTESTING]:
        backtester = tools[BOT_TOOLS_BACKTESTING]
        return backtester.get_report()
    return {}