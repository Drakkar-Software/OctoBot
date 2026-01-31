#  Drakkar-Software OctoBot-Trading
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
import decimal

import octobot_commons.logging as logging

import octobot_trading.util as util
import octobot_trading.constants as constants

LOGGER = logging.get_logger(constants.API_LOGGER_TAG)


def get_trader(exchange_manager):
    return exchange_manager.trader


def has_trader(exchange_manager):
    return exchange_manager.trader is not None


def is_trader_enabled_in_config_from_exchange_manager(exchange_manager) -> bool:
    return exchange_manager.trader.enabled(exchange_manager.config)


def is_trader_existing_and_enabled(exchange_manager) -> bool:
    return False if (exchange_manager.exchange_only or exchange_manager.trader is None) else (
        exchange_manager.trader.is_enabled
    )


def is_trader_enabled(exchange_manager) -> bool:
    return exchange_manager.trader.is_enabled


def is_trader_enabled_in_config(config) -> bool:
    return util.is_trader_enabled(config)


def is_trader_simulator_enabled_in_config(config) -> bool:
    return util.is_trader_simulator_enabled(config)


def set_trading_enabled(exchange_manager, enabled: bool) -> None:
    exchange_manager.trader.set_is_enabled(enabled)


def is_trader_simulated(exchange_manager) -> bool:
    return exchange_manager.is_trader_simulated


def get_trader_risk(exchange_manager) -> float:
    return exchange_manager.trader.risk


def set_trader_risk(exchange_manager, risk: decimal.Decimal) -> float:
    return exchange_manager.trader.set_risk(decimal.Decimal(risk))


async def sell_all_everything_for_reference_market(
    exchange_manager, force_if_disabled: bool = True
) -> list:
    return await exchange_manager.trader.sell_all(force_if_disabled=force_if_disabled)


async def sell_currency_for_reference_market(
    exchange_manager, currency: str, force_if_disabled: bool = True
) -> list:
    return await exchange_manager.trader.sell_all([currency], force_if_disabled=force_if_disabled)


def get_current_bot_live_id(config):
    return util.get_current_bot_live_id(config)
