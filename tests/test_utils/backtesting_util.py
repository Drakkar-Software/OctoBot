import logging

from config.cst import CONFIG_BACKTESTING, CONFIG_CATEGORY_NOTIFICATION, CONFIG_TRADER, CONFIG_SIMULATOR, \
    CONFIG_ENABLED_OPTION, CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS
from octobot import OctoBot
from tests.test_utils.config import load_test_config
from backtesting.backtesting import Backtesting


def create_backtesting_config(wanted_symbols=["BTC/USDT"], filter_symbols=True):
    # launch a bot
    config = load_test_config()

    if filter_symbols:
        filter_wanted_symbols(config, wanted_symbols)

    # setup backtesting config
    add_config_default_backtesting_values(config)

    return config


def add_config_default_backtesting_values(config):
    config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
    config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_ENABLED_OPTION] = False
    config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
    config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True


def filter_wanted_symbols(config, wanted_symbols):
    # filters to keep only relevant currencies
    wanted_symbols_set = set(wanted_symbols)
    for cryptocurrency, symbols in config[CONFIG_CRYPTO_CURRENCIES].items():
        if not wanted_symbols_set.intersection(symbols[CONFIG_CRYPTO_PAIRS]):
            config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency] = {CONFIG_CRYPTO_PAIRS: []}


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
    return Backtesting.get_profitability(bot)
