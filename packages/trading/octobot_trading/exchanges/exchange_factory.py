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
import asyncio
import typing

import trading_backend

import octobot_commons.authentication as authentication
import octobot_trading.errors as errors
import octobot_trading.exchanges as exchanges


async def create_exchanges(exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]]):
    if exchange_manager.is_sandboxed and not exchange_manager.exchange_only:
        exchange_manager.logger.info(f"Using sandbox exchange for {exchange_manager.exchange_name}")

    if exchange_manager.is_backtesting:
        # simulated : create exchange simulator instance
        await create_simulated_exchange(exchange_manager, exchange_config_by_exchange)
        exchange_manager.load_constants()
    else:
        # real : create a rest or websocket exchange instance
        await create_real_exchange(exchange_manager, exchange_config_by_exchange)
        exchange_manager.load_constants()
        await initialize_real_exchange(exchange_manager)

    if not exchange_manager.exchange_only:
        # create exchange producers if necessary
        await exchanges.create_exchange_producers(exchange_manager)

    if exchange_manager.is_backtesting:
        await init_simulated_exchange(exchange_manager)

    exchange_manager.exchange_name = exchange_manager.exchange.name
    exchange_manager.is_ready = True


async def create_real_exchange(exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]]) -> None:
    """
    Create and initialize real REST exchange
    :param exchange_manager: the related exchange manager
    :param exchange_config_by_exchange: optional exchange configurations
    """
    if exchange_manager.preconfigured_exchange:
        exchange_manager.exchange = exchange_manager.preconfigured_exchange
        exchange_manager.exchange.exchange_manager = exchange_manager
    else:
        await _create_rest_exchange(exchange_manager, exchange_config_by_exchange)
    try:
        if exchange_manager.preconfigured_exchange is None:
            await exchange_manager.exchange.initialize()
        _create_exchange_backend(exchange_manager)
        if exchange_manager.exchange_only:
            return
        await _initialize_exchange_backend(exchange_manager)
    except errors.AuthenticationError as err:
        if (
            exchange_manager.without_auth or exchange_manager.exchange.requires_authentication(
                exchange_manager.exchange.tentacle_config, None, None
            )
            or exchange_manager.disable_unauth_retry
        ):
            # auth is required or already retried, don't loop
            exchange_manager.logger.warning(
                f"Authentication is required and raised an error: impossible to connect to "
                f"{exchange_manager.exchange_name} exchange: {err}"
            )
            raise
        exchange_manager.logger.error(
            f"Authentication error on {exchange_manager.exchange_name}, retrying without authentication..."
        )
        exchange_manager.without_auth = True
        await create_real_exchange(exchange_manager, exchange_config_by_exchange)
        return


async def initialize_real_exchange(exchange_manager):
    if not exchange_manager.exchange_only:
        await exchanges.create_exchange_channels(exchange_manager)

    # create Websocket exchange if possible
    if not exchange_manager.rest_only:
        # search for websocket
        if exchanges.check_web_socket_config(exchange_manager.config, exchange_manager.exchange.name):
            await exchanges.search_and_create_websocket(exchange_manager)


def _create_exchange_backend(exchange_manager):
    try:
        exchange_manager.exchange_backend = trading_backend.exchange_factory.create_exchange_backend(
            exchange_manager.exchange
        )
    except Exception as e:
        exchange_manager.logger.exception(e, True, f"Error when creating exchange backend: {e}")


async def _initialize_exchange_backend(exchange_manager):
    if exchange_manager.exchange_backend is not None and exchange_manager.exchange.authenticated() \
            and not exchange_manager.is_trader_simulated:
        exchange_manager.logger.debug(await exchange_manager.exchange_backend.initialize())
        initial_is_broker_enabled = exchange_manager.is_broker_enabled
        try:
            exchange_manager.is_broker_enabled, _ = await exchange_manager.exchange_backend.is_valid_account()
            exchange_manager.logger.debug(f"Broker rebate enabled: {exchange_manager.is_broker_enabled}")
        except Exception as err:
            exchange_manager.is_broker_enabled = initial_is_broker_enabled
            exchange_manager.logger.debug(f"Error when checking account broker state: {err}")


async def _is_supporting_octobot() -> bool:
    try:
        authenticator = authentication.Authenticator.instance()
        if not authenticator.is_initialized():
            initialization_timeout = 5
            await authenticator.await_initialization(initialization_timeout)
        if authenticator.user_account.supports.is_supporting():
            return True
    except asyncio.TimeoutError:
        pass
    return False


async def _create_rest_exchange(
    exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]]
) -> None:
    """
    create REST based on ccxt exchange
    :param exchange_manager: the related exchange manager
    """
    await _search_and_create_rest_exchange(exchange_manager, exchange_config_by_exchange)

    if not exchange_manager.exchange:
        raise Exception(f"Can't create an exchange instance that match the exchange configuration ({exchange_manager})")


async def create_simulated_exchange(exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]]):
    exchange_manager.exchange = exchanges.ExchangeSimulator(
        exchange_manager.config, exchange_manager, exchange_manager.backtesting,
        exchange_config_by_exchange=exchange_config_by_exchange
    )

    await exchange_manager.exchange.initialize()
    _initialize_simulator_time_frames(exchange_manager)
    exchange_manager.exchange_config.set_config_time_frame()
    exchange_manager.exchange_config.set_config_traded_pairs()
    await exchanges.create_exchange_channels(exchange_manager)


async def init_simulated_exchange(exchange_manager):
    await exchange_manager.exchange.create_backtesting_exchange_producers()


async def _search_and_create_rest_exchange(
    exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]]
) -> None:
    """
    Create a rest exchange if a RestExchange matching class is found
    :param exchange_manager: the related exchange manager
    """
    rest_exchange_class = exchanges.get_rest_exchange_class(
        exchange_manager.exchange_name, exchange_manager.tentacles_setup_config, exchange_config_by_exchange
    )
    if rest_exchange_class:
        if rest_exchange_class.HAS_FETCHED_DETAILS:
            await rest_exchange_class.fetch_exchange_config(exchange_config_by_exchange, exchange_manager)
        exchange_manager.exchange = rest_exchange_class(
            config=exchange_manager.config, exchange_manager=exchange_manager,
            exchange_config_by_exchange=exchange_config_by_exchange
        )


def _initialize_simulator_time_frames(exchange_manager):
    """
    Initialize simulator client time frames
    :param exchange_manager: the related exchange manager
    """
    exchange_manager.client_time_frames = exchange_manager.exchange.get_available_time_frames()
