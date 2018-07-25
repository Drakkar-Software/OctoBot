import ccxt

from config.cst import CONFIG_EVALUATOR
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
    for service in AbstractService.__subclasses__():
        srv = service()
        services[srv.get_type()] = srv
    return services


def get_symbol_list(exchanges):
    result = []

    for exchange in exchanges:
        try:
            inst = getattr(ccxt, exchange)({'verbose': False})
            inst.load_markets()
            result += inst.symbols
        except Exception:
            pass

    return list(set(result))
