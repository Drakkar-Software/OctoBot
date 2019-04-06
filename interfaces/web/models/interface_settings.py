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

import copy

from interfaces import get_bot
from config import CONFIG_WATCHED_SYMBOLS, CONFIG_FILE, TEMP_RESTORE_CONFIG_FILE, CONFIG_CRYPTO_CURRENCIES, \
    CONFIG_CRYPTO_PAIRS
from tools.config_manager import ConfigManager


def _get_config():
    return get_bot().edited_config


def _symbol_in_currencies_config(config, symbol):
    return any(symbol in crypto_currency_data[CONFIG_CRYPTO_PAIRS]
               for crypto_currency_data in config[CONFIG_CRYPTO_CURRENCIES].values())


def get_watched_symbols():
    config = _get_config()
    if CONFIG_WATCHED_SYMBOLS not in config:
        config[CONFIG_WATCHED_SYMBOLS] = []
    else:
        for symbol in copy.copy(config[CONFIG_WATCHED_SYMBOLS]):
            if not _symbol_in_currencies_config(config, symbol):
                config[CONFIG_WATCHED_SYMBOLS].remove(symbol)
    return config[CONFIG_WATCHED_SYMBOLS]


def add_watched_symbol(symbol):
    watched_symbols = get_watched_symbols()
    watched_symbols.append(symbol)
    return _save_edition()


def remove_watched_symbol(symbol):
    watched_symbols = get_watched_symbols()
    if symbol in watched_symbols:
        watched_symbols.remove(symbol)
    return _save_edition()


def _save_edition():
    ConfigManager.simple_save_config_update(_get_config())
    return True
