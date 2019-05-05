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
from copy import deepcopy

from backtesting.backtesting import Backtesting
from backtesting.collector.data_file_manager import interpret_file_name, is_valid_ending
from config import CONFIG_BACKTESTING, CONFIG_CATEGORY_NOTIFICATION, CONFIG_TRADER, CONFIG_TRADING, \
    CONFIG_SIMULATOR, CONFIG_ENABLED_OPTION, CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS, \
    CONFIG_BACKTESTING_DATA_FILES, CONFIG_TRADING_TENTACLES, CONFIG_EVALUATOR, CONFIG_TRADER_RISK, \
    CONFIG_DATA_COLLECTOR_PATH, CONFIG_TRADER_REFERENCE_MARKET, CONFIG_STARTING_PORTFOLIO, \
    CONFIG_BACKTESTING_OTHER_MARKETS_STARTING_PORTFOLIO, DEFAULT_REFERENCE_MARKET, CONFIG_SIMULATOR_FEES
from config.config import load_config
from core.octobot import OctoBot
from services.web_service import WebService
from tools.logging.logging_util import get_logger, BotLogger
from tools.symbol_util import split_symbol


def create_blank_config_using_loaded_one(loaded_config, other_config=None):
    new_config = other_config if other_config else load_config()
    trading_tentacles_config = deepcopy(loaded_config[CONFIG_TRADING_TENTACLES])
    risk = deepcopy(loaded_config[CONFIG_TRADING][CONFIG_TRADER_RISK])
    starting_portfolio = deepcopy(loaded_config[CONFIG_SIMULATOR][CONFIG_STARTING_PORTFOLIO])
    fees_config = deepcopy(loaded_config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES])
    new_config[CONFIG_TRADING_TENTACLES] = trading_tentacles_config
    new_config[CONFIG_TRADING][CONFIG_TRADER_RISK] = risk
    new_config[CONFIG_SIMULATOR][CONFIG_STARTING_PORTFOLIO] = starting_portfolio
    new_config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES] = fees_config
    new_config[CONFIG_EVALUATOR] = deepcopy(loaded_config[CONFIG_EVALUATOR])
    add_config_default_backtesting_values(new_config)
    return new_config


def get_standalone_backtesting_bot(config, data_files):
    config_to_use = create_blank_config_using_loaded_one(config)
    config_to_use[CONFIG_CRYPTO_CURRENCIES] = {}
    config_to_use[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES] = []
    # do not activate web interface on standalone backtesting bot
    WebService.enable(config_to_use, False)
    ignored_files = []
    reference_market = _get_reference_market(data_files)
    if DEFAULT_REFERENCE_MARKET != reference_market:
        _switch_reference_market(config_to_use, reference_market)
    if data_files:
        for data_file_to_use in data_files:
            _, file_symbol, _, _ = interpret_file_name(data_file_to_use)
            currency, _ = split_symbol(file_symbol)
            full_file_path = CONFIG_DATA_COLLECTOR_PATH + data_file_to_use
            ending = f".{full_file_path.split('.')[-1]}"
            full_file_path += full_file_path if not is_valid_ending(ending) else ""
            if currency not in config_to_use[CONFIG_CRYPTO_CURRENCIES]:
                config_to_use[CONFIG_CRYPTO_CURRENCIES][currency] = {CONFIG_CRYPTO_PAIRS: []}
            if file_symbol not in config_to_use[CONFIG_CRYPTO_CURRENCIES][currency][CONFIG_CRYPTO_PAIRS]:
                config_to_use[CONFIG_CRYPTO_CURRENCIES][currency][CONFIG_CRYPTO_PAIRS].append(file_symbol)
                config_to_use[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES].append(full_file_path)
            else:
                ignored_files.append(data_file_to_use)

    return create_backtesting_bot(config_to_use), ignored_files


def create_backtesting_config(config, wanted_symbols=None, filter_symbols=True):
    if wanted_symbols is None:
        wanted_symbols = ["BTC/USDT"]
    if filter_symbols:
        filter_wanted_symbols(config, wanted_symbols)

    # setup backtesting config
    add_config_default_backtesting_values(config)

    return config


def add_config_default_backtesting_values(config):
    if CONFIG_BACKTESTING not in config:
        config[CONFIG_BACKTESTING] = {}
    config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
    config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_ENABLED_OPTION] = False
    config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
    config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True


def filter_wanted_symbols(config, wanted_symbols):
    # filters to keep only relevant currencies
    found_symbol = False
    wanted_symbols_set = set(wanted_symbols)
    for cryptocurrency, symbols in config[CONFIG_CRYPTO_CURRENCIES].items():
        if not wanted_symbols_set.intersection(symbols[CONFIG_CRYPTO_PAIRS]):
            config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency] = {CONFIG_CRYPTO_PAIRS: []}
        else:
            found_symbol = True

    if not found_symbol:
        raise SymbolNotFoundException(f"No symbol matching {wanted_symbols} found in configuration file.")


def update_starting_portfolio_if_required(config, wanted_symbol):
    quote, base = split_symbol(wanted_symbol)
    if DEFAULT_REFERENCE_MARKET != base:
        _switch_reference_market(config, base)


def create_backtesting_bot(config) -> OctoBot:
    return OctoBot(config)


async def start_backtesting_bot(bot, in_thread=False, watcher=None):
    BotLogger.reset_backtesting_errors()
    await initialize_bot(bot)

    # fix backtesting exit
    for exchange in bot.get_exchanges_list():
        exchange_inst = bot.get_exchanges_list()[exchange].get_exchange()
        try:
            exchange_inst.backtesting.force_exit_at_end = False
        except Exception:
            get_logger(f"fail to stop force exit for exchange {exchange_inst.get_name()}")

    if not bot.get_symbols_tasks_manager():
        raise RuntimeError(f"No candles data for the current configuration. Please ensure the required data files for "
                           f"the activated symbol(s) are available. Symbol(s): {list(bot.get_symbols_list())}")

    if watcher is not None:
        bot.set_watcher(watcher)

    if in_thread:
        await start_bot(bot, True)
        return True
    else:
        await start_bot(bot)
        trader = next(iter(bot.get_exchange_trader_simulators().values()))
        return await Backtesting.get_profitability(trader)


async def start_bot(bot, run_in_new_thread=False):
    await bot.start(run_in_new_thread)


async def initialize_bot(bot):
    await bot.initialize()


def _switch_reference_market(config_to_use, market):
    config_to_use[CONFIG_TRADING][CONFIG_TRADER_REFERENCE_MARKET] = market
    config_to_use[CONFIG_SIMULATOR][CONFIG_STARTING_PORTFOLIO][market] = \
        CONFIG_BACKTESTING_OTHER_MARKETS_STARTING_PORTFOLIO


def _get_reference_market(data_files):
    reference_market = None
    for data_file in data_files:
        _, file_symbol, _, _ = interpret_file_name(data_file)
        currency, market = split_symbol(file_symbol)
        if reference_market is None:
            reference_market = market
        elif not reference_market == market:
            # more than one reference market in data_files: use first reference market
            return reference_market
    return reference_market if reference_market is not None else DEFAULT_REFERENCE_MARKET


class SymbolNotFoundException(Exception):
    pass
