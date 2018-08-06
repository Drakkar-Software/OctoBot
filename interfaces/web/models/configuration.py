import json
import logging

import ccxt
import requests

from config.cst import CONFIG_EVALUATOR, COIN_MARKET_CAP_CURRENCIES_LIST_URL, CONFIG_EXCHANGES, UPDATED_CONFIG_SEPARATOR
from interfaces import get_bot
from services import AbstractService
from tools.config_manager import ConfigManager


def get_global_config():
    return get_bot().get_config()


def get_global_startup_config():
    return get_bot().get_startup_config()


def get_evaluator_config():
    return get_bot().get_config()[CONFIG_EVALUATOR]


def get_evaluator_startup_config():
    return get_bot().get_startup_config()[CONFIG_EVALUATOR]


def update_evaluator_config(new_config):
    current_config = get_evaluator_config()
    try:
        ConfigManager.update_evaluator_config(new_config, current_config)
        return True
    except Exception:
        return False


def update_global_config(new_config):
    current_config = get_global_config()
    # try:
    ConfigManager.update_global_config(new_config, current_config)
    return True
    # except Exception:
    #     return False


def get_services_list():
    services = {}
    services_names = []
    for service in AbstractService.__subclasses__():
        srv = service()
        services[srv.get_type()] = srv
        services_names.append(srv.get_name())
    return services, services_names


def get_symbol_list(exchanges):
    result = []

    for exchange in exchanges:
        try:
            inst = getattr(ccxt, exchange)({'verbose': False})
            inst.load_markets()
            result += inst.symbols
        except Exception as e:
            logging.getLogger().error(f"error when loading symbol list for {exchange}: {e}")

    return list(set(result))


def get_all_symbol_list():
    try:
        currencies_list = json.loads(requests.get(COIN_MARKET_CAP_CURRENCIES_LIST_URL).text)
        return {
            currency_data["name"]: currency_data["symbol"]
            for currency_data in currencies_list["data"]
        }
    except Exception as e:
        logging.getLogger().error(f"Failed to get currencies list from coinmarketcap : {e}")


def get_full_exchange_list(remove_config_exchanges=False):
    g_config = get_bot().get_config()
    if remove_config_exchanges:
        user_exchanges = [e for e in g_config[CONFIG_EXCHANGES]]
        full_exchange_list = list(set(ccxt.exchanges) - set(user_exchanges))
    else:
        full_exchange_list = list(set(ccxt.exchanges))
    # can't handle exchanges containing UPDATED_CONFIG_SEPARATOR character in their name
    return [exchange for exchange in full_exchange_list if UPDATED_CONFIG_SEPARATOR not in exchange]


def get_current_exchange():
    g_config = get_bot().get_config()
    exchanges = g_config[CONFIG_EXCHANGES]
    if exchanges:
        return next(iter(exchanges))
    else:
        return "binance"
