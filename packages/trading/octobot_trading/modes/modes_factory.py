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
import octobot_commons.constants as constants
import octobot_commons.logging as logging

import octobot_trading.errors as errors

LOGGER_TAG = "TradingModeFactory"


async def create_trading_modes(
    config: dict,
    exchange_manager,
    trading_mode_class,
    bot_id: str,
    trading_config_by_trading_mode: dict = None,
    auto_start: bool = True,
) -> list:
    is_symbol_wildcard = trading_mode_class.get_is_symbol_wildcard()
    if is_symbol_wildcard or (not is_symbol_wildcard and exchange_manager.exchange_config.traded_symbol_pairs):
        return await _create_trading_modes(
            trading_mode_class=trading_mode_class,
            config=config,
            exchange_manager=exchange_manager,
            cryptocurrencies=exchange_manager.exchange_config.traded_cryptocurrencies,
            symbols=exchange_manager.exchange_config.traded_symbol_pairs,
            time_frames=exchange_manager.exchange_config.traded_time_frames,
            bot_id=bot_id,
            trading_config_by_trading_mode=trading_config_by_trading_mode,
            auto_start=auto_start,
        )
    # Do not create no symbol wildcard trading mode if no trading pair is available
    raise errors.TradingModeIncompatibility(
        f"As non symbol-wildcard trading mode, {trading_mode_class.get_name()} requires "
        f"at least one exchange trading pair to be initialized. "
        f"None of the required pairs are available on {exchange_manager.exchange_name}.")


async def _create_trading_modes(
    trading_mode_class,
    config: dict,
    exchange_manager,
    cryptocurrencies: dict = None,
    symbols: list = None,
    time_frames: list = None,
    bot_id: str = None,
    trading_config_by_trading_mode: dict = None,
    auto_start: bool = True
) -> list:
    trading_config_by_trading_mode = trading_config_by_trading_mode or {}
    return [
        await create_trading_mode(
            trading_mode_class=trading_mode_class,
            config=config,
            exchange_manager=exchange_manager,
            cryptocurrency=cryptocurrency,
            symbol=symbol,
            time_frame=time_frame,
            bot_id=bot_id,
            trading_config=trading_config_by_trading_mode.get(trading_mode_class.get_name()),
            auto_start=auto_start,
        )
        for cryptocurrency in _get_cryptocurrencies_to_create(trading_mode_class, cryptocurrencies)
        for symbol in _get_symbols_to_create(trading_mode_class, cryptocurrencies, cryptocurrency, symbols)
        for time_frame in _get_time_frames_to_create(trading_mode_class, time_frames)
    ]


async def create_trading_mode(
    trading_mode_class,
    config: dict,
    exchange_manager,
    cryptocurrency: str = None,
    symbol: str = None,
    time_frame: object = None,
    bot_id: str = None,
    trading_config: dict = None,
    auto_start: bool = True,
):
    try:
        trading_mode = trading_mode_class(config, exchange_manager)
        trading_mode.cryptocurrency = cryptocurrency
        trading_mode.symbol = symbol
        trading_mode.time_frame = time_frame
        trading_mode.bot_id = bot_id
        await trading_mode.initialize(trading_config=trading_config, auto_start=auto_start)
        logging.get_logger(f"{LOGGER_TAG}[{exchange_manager.exchange_name}]") \
            .debug(f"{trading_mode.get_name()} {'started' if auto_start else 'created'} for "
                   f"[cryptocurrency={cryptocurrency if cryptocurrency else constants.CONFIG_WILDCARD},"
                   f" symbol={symbol if symbol else constants.CONFIG_WILDCARD},"
                   f" time_frame={time_frame if time_frame else constants.CONFIG_WILDCARD}]")
        return trading_mode
    except RuntimeError as e:
        logging.get_logger(LOGGER_TAG).error(e.args[0])
        raise e


def create_temporary_trading_mode_with_local_config(trading_mode_class, config, trading_config):
    trading_mode = trading_mode_class(config, None)
    trading_mode.trading_config = trading_config
    return trading_mode


def _get_cryptocurrencies_to_create(trading_mode_class, cryptocurrencies):
    return list(cryptocurrencies.keys()) \
        if cryptocurrencies and not trading_mode_class.get_is_cryptocurrency_wildcard() else [None]


def _get_symbols_to_create(trading_mode_class, cryptocurrencies, cryptocurrency, symbols):
    currency_symbols = symbols
    if cryptocurrency is not None:
        currency_symbols = cryptocurrencies.get(cryptocurrency, [])
    return currency_symbols if currency_symbols and not trading_mode_class.get_is_symbol_wildcard() else [None]


def _get_time_frames_to_create(trading_mode_class, time_frames):
    return time_frames if time_frames and not trading_mode_class.get_is_time_frame_wildcard() else [None]
