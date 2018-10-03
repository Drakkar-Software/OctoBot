from interfaces import get_bot
from config.cst import CONFIG_WATCHED_SYMBOLS, CONFIG_FILE, TEMP_RESTORE_CONFIG_FILE
from tools.config_manager import ConfigManager


def _get_config():
    return get_bot().get_edited_config()


def get_watched_symbols():
    config = _get_config()
    if CONFIG_WATCHED_SYMBOLS not in config:
        config[CONFIG_WATCHED_SYMBOLS] = []
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
    ConfigManager.save_config(CONFIG_FILE, _get_config(), TEMP_RESTORE_CONFIG_FILE)
    return True
