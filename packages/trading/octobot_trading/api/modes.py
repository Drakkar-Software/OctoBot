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

import octobot_trading.modes as modes
import octobot_commons.constants as commons_constants


def get_trading_modes(exchange_manager) -> list:
    return exchange_manager.trading_modes


def get_trading_mode_symbol(trading_mode) -> list:
    return trading_mode.symbol


def is_trading_mode_symbol_wildcard(trading_mode) -> bool:
    return trading_mode.get_is_symbol_wildcard()


def get_trading_mode_followed_strategy_signals_identifier(trading_mode) -> str:
    if trading_mode.is_following_trading_signals():
        return trading_mode.trading_config.get(commons_constants.CONFIG_TRADING_SIGNALS_STRATEGY, "")
    return None


def get_trading_mode_current_state(trading_mode) -> tuple:
    return trading_mode.get_current_state()


def get_activated_trading_mode(tentacles_setup_config) -> modes.AbstractTradingMode.__class__:
    return modes.get_activated_trading_mode(tentacles_setup_config)


async def create_trading_modes(config: dict,
                               exchange_manager: object,
                               trading_mode_class: modes.AbstractTradingMode.__class__,
                               bot_id: str) -> list:
    return await modes.create_trading_modes(config=config,
                                            exchange_manager=exchange_manager,
                                            trading_mode_class=trading_mode_class,
                                            bot_id=bot_id)


async def create_trading_mode(trading_mode_class: modes.AbstractTradingMode.__class__,
                              config: dict,
                              exchange_manager: object,
                              cryptocurrency: str = None,
                              symbol: str = None,
                              time_frame: object = None,
                              bot_id: str = None) -> modes.AbstractTradingMode:
    return await modes.create_trading_mode(trading_mode_class=trading_mode_class,
                                           config=config,
                                           exchange_manager=exchange_manager,
                                           cryptocurrency=cryptocurrency,
                                           symbol=symbol,
                                           time_frame=time_frame,
                                           bot_id=bot_id)
