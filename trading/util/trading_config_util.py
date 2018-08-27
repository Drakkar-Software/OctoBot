from config.cst import CONFIG_TRADING, CONFIG_TRADING_TENTACLES, CONFIG_TRADING_FILE_PATH
from trading.trader import modes
from tools.class_inspector import get_deep_class_from_string, get_class_from_string
from trading.trader.modes.abstract_trading_mode import AbstractTradingMode
from tools.errors import ConfigTradingError


def get_activated_trading_mode(config):
    if CONFIG_TRADING in config and CONFIG_TRADING_TENTACLES in config[CONFIG_TRADING]:
        trading_modes = [class_str
                         for class_str, activated in config[CONFIG_TRADING][CONFIG_TRADING_TENTACLES].items()
                         if activated and get_class_from_string(class_str, AbstractTradingMode, modes)]

        if len(trading_modes) > 1:
            raise ConfigTradingError(
                f"More than one activated trading mode found in your {CONFIG_TRADING_FILE_PATH} file, "
                f"please activate only one")

        elif trading_modes:
            trading_mode_class = get_deep_class_from_string(trading_modes[0], modes)

            if trading_mode_class is not None:
                return trading_mode_class

    raise ConfigTradingError(f"Please activate a valid trading mode in your {CONFIG_TRADING_FILE_PATH} file")
