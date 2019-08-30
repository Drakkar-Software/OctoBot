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
from octobot_commons.config import load_config, get_user_config

from octobot_commons.config_manager import _handle_encrypted_value, dump_json, save_config
from octobot_commons.constants import TEMP_RESTORE_CONFIG_FILE, CONFIG_ENABLED_OPTION
from octobot_commons.logging.logging_util import get_logger
from octobot_trading.constants import CONFIG_EXCHANGES, CONFIG_EXCHANGE_ENCRYPTED_VALUES, CONFIG_SIMULATOR, \
    CONFIG_TRADER
from octobot_trading.util import is_trader_enabled, is_trader_simulator_enabled


def config_health_check(config):
    # 1 ensure api key encryption
    should_replace_config = False
    if CONFIG_EXCHANGES in config:
        for exchange, exchange_config in config[CONFIG_EXCHANGES].items():
            for key in CONFIG_EXCHANGE_ENCRYPTED_VALUES:
                try:
                    if not _handle_encrypted_value(key, exchange_config, verbose=True):
                        should_replace_config = True
                except Exception as e:
                    get_logger().error(f"Exception when checking exchange config encryption: {e}")
                    get_logger().exception(e)

    # 2 ensure single trader activated
    try:
        trader_enabled = is_trader_enabled(config)
        if trader_enabled:
            simulator_enabled = is_trader_simulator_enabled(config)
            if simulator_enabled:
                get_logger().error(f"Impossible to activate a trader simulator additionally to a real trader, "
                                   f"simulator deactivated.")
                config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = False
                should_replace_config = True
    except KeyError as e:
        get_logger().error(f"KeyError when checking traders activation: {e}. Activating trader simulator.")
        get_logger().exception(e)
        config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True
        config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
        should_replace_config = True

    # 3 save fixed config if necessary
    if should_replace_config:
        try:
            save_config(get_user_config(), config, TEMP_RESTORE_CONFIG_FILE, json_data=dump_json(config))
            return config
        except Exception as e:
            get_logger().error(f"Save of the health checked config failed : {e}, will use the initial config")
            return load_config(error=False, fill_missing_fields=True)


def jsonify_config(config):
    # check exchange keys encryption
    for exchange, exchange_config in config[CONFIG_EXCHANGES].items():
        try:
            for key in CONFIG_EXCHANGE_ENCRYPTED_VALUES:
                _handle_encrypted_value(key, CONFIG_EXCHANGES)
        except Exception:
            config[CONFIG_EXCHANGES][exchange] = {key: "" for key in CONFIG_EXCHANGE_ENCRYPTED_VALUES}

    return dump_json(config)
