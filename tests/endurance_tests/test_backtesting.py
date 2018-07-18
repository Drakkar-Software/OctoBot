import logging

from config.cst import TimeFrames, CONFIG_BACKTESTING, CONFIG_CATEGORY_NOTIFICATION, CONFIG_TRADER, CONFIG_SIMULATOR, \
    CONFIG_ENABLED_OPTION
from octobot import OctoBot
from tests.test_utils.config import load_test_config


def create_backtesting_config():
    # launch a bot
    config = load_test_config()

    # setup backtesting config
    config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
    config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_ENABLED_OPTION] = False
    config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
    config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True

    return config


def create_backtesting_bot(config):
    bot = OctoBot(config)
    return bot


def start_backtesting_bot(bot):
    bot.create_exchange_traders()

    # fix backtesting exit
    for exchange in bot.exchanges_list:
        exchange_inst = bot.exchanges_list[exchange].get_exchange()
        try:
            exchange_inst.backtesting.force_exit_at_end = False
        except Exception:
            logging.getLogger(f"fail to stop forcing exit for exchange {exchange_inst.get_name()}")

    bot.create_evaluation_threads()
    bot.start_threads()
    bot.join_threads()


def test_simple_backtesting():
    config = create_backtesting_config()
    bot = create_backtesting_bot(config)
    start_backtesting_bot(bot)


def test_multiple_backtesting():
    for _ in range(10):
        config = create_backtesting_config()
        bot = create_backtesting_bot(config)
        start_backtesting_bot(bot)
