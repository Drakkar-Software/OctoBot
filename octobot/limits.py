#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import octobot.constants as constants
import octobot_commons.constants as common_constants
import octobot_commons.logging as logging
import octobot_trading.api as trading_api


def _apply_exchanges_limits(dict_config, logger, limit):
    exchanges = [
        f"{exchange}[{config.get(common_constants.CONFIG_EXCHANGE_TYPE, common_constants.CONFIG_EXCHANGE_SPOT)}]"
        for exchange, config in dict_config[common_constants.CONFIG_EXCHANGES].items()
        if config.get(common_constants.CONFIG_ENABLED_OPTION, True)
    ]
    if limit != constants.UNLIMITED_ALLOWED and len(exchanges) > limit:
        enabled_exchanges = []
        for exchange, config in dict_config[common_constants.CONFIG_EXCHANGES].items():
            if config.get(common_constants.CONFIG_ENABLED_OPTION, True):
                if len(enabled_exchanges) < limit:
                    enabled_exchanges.append(exchange)
                else:
                    config[common_constants.CONFIG_ENABLED_OPTION] = False
                    logger.warning("Disabled : " + exchange)
        logger.error(f"Too many enabled exchanges, maximum allowed is {limit}. Enabled : {enabled_exchanges}")


def _apply_symbols_limits(dict_config, logger, limit):
    if limit != constants.UNLIMITED_ALLOWED:
        enabled_symbols = []
        for currency, crypto_currency_data in dict_config[common_constants.CONFIG_CRYPTO_CURRENCIES].items():
            if crypto_currency_data.get(common_constants.CONFIG_ENABLED_OPTION, True):
                if len(enabled_symbols) >= limit:
                    crypto_currency_data[common_constants.CONFIG_ENABLED_OPTION] = False
                    logger.warning(f"Disabled : {currency}")
                    continue
                updated_symbols = []
                for symbol in crypto_currency_data[common_constants.CONFIG_CRYPTO_PAIRS]:
                    if symbol == common_constants.CONFIG_SYMBOLS_WILDCARD[0] \
                            or symbol == common_constants.CONFIG_SYMBOLS_WILDCARD:
                        crypto_currency_data[common_constants.CONFIG_ENABLED_OPTION] = False
                        logger.warning(f"Disabled wildcard symbol for {currency}")
                        break
                    else:
                        if len(enabled_symbols) < limit:
                            enabled_symbols.append(symbol)
                            updated_symbols.append(symbol)
                        else:
                            logger.warning(f"Disabled : {symbol}")
                crypto_currency_data[common_constants.CONFIG_CRYPTO_PAIRS] = updated_symbols
        if len(trading_api.get_config_symbols(dict_config, True)) > limit:
            logger.error(f"Too many trading pairs, maximum allowed is {limit}. Enabled : {enabled_symbols}")


def apply_config_limits(configuration):
    logger = logging.get_logger("ConfigurationLimits")
    try:
        _apply_exchanges_limits(configuration.config, logger, constants.MAX_ALLOWED_EXCHANGES)
        _apply_symbols_limits(configuration.config, logger, constants.MAX_ALLOWED_SYMBOLS)
    except Exception as err:
        logger.exception(err, True, f"Error when applying limits: {err}")
