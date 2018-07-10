from config.cst import CONFIG_EVALUATOR
from interfaces import get_bot
from tools.config_manager import ConfigManager


def get_evaluator_config():
    return get_bot().get_config()[CONFIG_EVALUATOR]


def get_evaluator_startup_config():
    return get_bot().get_startup_config()[CONFIG_EVALUATOR]


def reset_evaluator_config():
    return update_evaluator_config(get_evaluator_startup_config())


def update_evaluator_config(new_config):
    current_config = get_bot().get_config()[CONFIG_EVALUATOR]
    try:
        ConfigManager.update_evaluator_config(new_config, current_config)
        return True
    except Exception:
        return False
