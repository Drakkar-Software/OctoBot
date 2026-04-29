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
import asyncio
import typing

import octobot_commons.logging as logging

import octobot_trading.util as util
import octobot_trading.constants as constants

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges

LOGGER = logging.get_logger(constants.API_LOGGER_TAG)


def get_trader(exchange_manager: "octobot_trading.exchanges.ExchangeManager") -> "octobot_trading.exchanges.Trader":
    return exchange_manager.trader


def has_trader(exchange_manager: "octobot_trading.exchanges.ExchangeManager") -> bool:
    return exchange_manager.trader is not None


def is_trader_enabled_in_config_from_exchange_manager(exchange_manager: "octobot_trading.exchanges.ExchangeManager") -> bool:
    return exchange_manager.trader.enabled(exchange_manager.config)


def is_trader_existing_and_enabled(exchange_manager: "octobot_trading.exchanges.ExchangeManager") -> bool:
    return False if (exchange_manager.exchange_only or exchange_manager.trader is None) else (
        exchange_manager.trader.is_enabled
    )


def is_trader_enabled(exchange_manager: "octobot_trading.exchanges.ExchangeManager") -> bool:
    return exchange_manager.trader.is_enabled


def is_trader_enabled_in_config(config: dict) -> bool:
    return util.is_trader_enabled(config)


def is_trader_simulator_enabled_in_config(config: dict) -> bool:
    return util.is_trader_simulator_enabled(config)


def set_trading_enabled(exchange_manager: "octobot_trading.exchanges.ExchangeManager", enabled: bool) -> None:
    exchange_manager.trader.set_is_enabled(enabled)


def is_trader_simulated(exchange_manager: "octobot_trading.exchanges.ExchangeManager") -> bool:
    return exchange_manager.is_trader_simulated


def get_trader_risk(exchange_manager: "octobot_trading.exchanges.ExchangeManager") -> decimal.Decimal:
    return exchange_manager.trader.risk


def set_trader_risk(exchange_manager: "octobot_trading.exchanges.ExchangeManager", risk: decimal.Decimal) -> decimal.Decimal:
    return exchange_manager.trader.set_risk(decimal.Decimal(risk))


async def sell_all_everything_for_reference_market(
    exchange_manager: "octobot_trading.exchanges.ExchangeManager", force_if_disabled: bool = True
) -> list:
    return await exchange_manager.trader.sell_all(force_if_disabled=force_if_disabled) # type: ignore


async def sell_currency_for_reference_market(
    exchange_manager: "octobot_trading.exchanges.ExchangeManager", currency: str, force_if_disabled: bool = True
) -> list:
    return await exchange_manager.trader.sell_all([currency], force_if_disabled=force_if_disabled) # type: ignore


def get_current_bot_live_id(config: dict) -> str:
    return util.get_current_bot_live_id(config)


def are_all_trading_modes_stoppped_and_trader_paused(exchange_manager: "octobot_trading.exchanges.ExchangeManager") -> bool:
    return all(
        trading_mode.stopped_strategy_execution()
        for trading_mode in exchange_manager.trading_modes
    ) and not exchange_manager.trader.is_enabled


async def stop_all_trading_modes_and_pause_trader(exchange_manager: "octobot_trading.exchanges.ExchangeManager", reason_description: typing.Optional[str]):
    all_trading_modes = exchange_manager.trading_modes
    if not all_trading_modes:
        set_trading_enabled(exchange_manager, False)
        return
    exchange_name = exchange_manager.exchange_name
    # stop all market making trading modes of this bot, on all exchanges
    exchange_manager.logger.info(
        f"Stopping all {len(all_trading_modes)} [{exchange_name}] trading modes"
    )
    await asyncio.gather(*[
        trading_mode.stop_strategy_execution(reason_description)
        for trading_mode in all_trading_modes
    ])
    exchange_manager.logger.info(
        f"All {len(all_trading_modes)} trading modes have been stopped. Pausing [{exchange_name}] trader"
    )
    # now that orders have been cancelled, disable trader to prevent further orders from being created
    set_trading_enabled(exchange_manager, False)
