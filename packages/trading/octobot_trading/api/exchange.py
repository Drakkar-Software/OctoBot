# pylint: disable=protected-access
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
import contextlib
import typing

import trading_backend

import octobot_commons.symbols as commons_symbols
import octobot_commons.enums as commons_enums

import octobot_trading.constants
import octobot_trading.enums
import octobot_trading.exchanges as exchanges
import octobot_trading.exchange_data as exchange_data

import octobot_backtesting.api as backtesting_api


def create_exchange_builder(config, exchange_name: str) -> exchanges.ExchangeBuilder:
    return exchanges.create_exchange_builder_instance(config, exchange_name)


async def stop_exchange(exchange_manager) -> None:
    await exchange_manager.stop()


def get_exchange_configurations_from_exchange_name(exchange_name: str) -> typing.Optional[dict]:
    return exchanges.Exchanges.instance().get_exchanges(exchange_name)


def get_exchange_manager_from_exchange_name_and_id(exchange_name: str, exchange_id: str) -> "exchanges.ExchangeManager":
    return exchanges.Exchanges.instance().get_exchange(exchange_name, exchange_id).exchange_manager


def get_exchange_managers_from_exchange_name(exchange_name: str) -> list["exchanges.ExchangeManager"]:
    return [
        exchange_configuration.exchange_manager
        for exchange_configuration in get_exchange_configurations_from_exchange_name(exchange_name).values()
    ]


async def get_ccxt_exchange_available_time_frames(
        exchange_name: str,
        tentacles_setup_config
) -> list:
    """
    When using CCXT, prefer using the sync lib since no request is required to get time frames
    :param exchange_name: name of the exchange
    :return: the list of time frames
    """
    try:
        exchange_configurations = get_exchange_configurations_from_exchange_name(exchange_name)
        if exchange_configurations:
            # first try in available exchanges
            for exchange_configuration in exchange_configurations.values():
                return exchange_configuration.exchange_manager.client_time_frames
        return []
    except KeyError:
        async with get_new_ccxt_client(exchange_name, {}, tentacles_setup_config, False) as ccxt_exchange:
            return ccxt_exchange.timeframes


def get_exchange_available_required_time_frames(exchange_name: str, exchange_id: str) -> list:
    return exchanges.Exchanges.instance().get_exchange(exchange_name, exchange_id).available_required_time_frames


# prefer get_exchange_configurations_from_exchange_name when possible
def get_exchange_configuration_from_exchange_id(exchange_id: str) -> exchanges.ExchangeConfiguration:
    for exchange_configs in exchanges.Exchanges.instance().exchanges.values():
        for exchange_config in exchange_configs.values():
            if exchange_config.exchange_manager.id == exchange_id:
                return exchange_config
    raise KeyError(f"No exchange configuration with id: {exchange_id}")


# prefer get_exchange_manager_from_exchange_name_and_id when possible
def get_exchange_manager_from_exchange_id(exchange_id: str) -> exchanges.ExchangeManager:
    try:
        return get_exchange_configuration_from_exchange_id(exchange_id).exchange_manager
    except KeyError:
        raise KeyError(f"No exchange manager with id: {exchange_id}")


def get_exchange_managers_from_exchange_ids(exchange_ids) -> list:
    return [get_exchange_manager_from_exchange_id(manager_id) for manager_id in exchange_ids]


def get_trading_exchanges(exchange_managers) -> list:
    return [exchange_manager for exchange_manager in exchange_managers
            if exchange_manager.is_trading]


def is_exchange_trading(exchange_manager) -> bool:
    return exchange_manager.is_trading


def get_exchange_manager_id(exchange_manager) -> str:
    return exchange_manager.id


def get_exchange_manager_is_sandboxed(exchange_manager) -> bool:
    return exchange_manager.is_sandboxed


def get_exchange_current_time(exchange_manager) -> float:
    return exchange_manager.exchange.get_exchange_current_time()


def get_exchange_backtesting_time_window(exchange_manager) -> typing.Tuple[float, float]:
    return backtesting_api.get_backtesting_starting_time(
        exchange_manager.exchange.backtesting
    ), backtesting_api.get_backtesting_ending_time(
        exchange_manager.exchange.backtesting
    )


def get_exchange_allowed_time_lag(exchange_manager) -> float:
    return exchange_manager.exchange.allowed_time_lag


def get_exchange_id_from_matrix_id(exchange_name: typing.Optional[str], matrix_id: str) -> typing.Optional[str]:
    if not exchange_name:
        return None
    
    exchange_configurations = get_exchange_configurations_from_exchange_name(exchange_name)
    if exchange_configurations:
        for exchange_configuration in exchange_configurations.values():
            if exchange_configuration.matrix_id == matrix_id:
                return get_exchange_manager_id(exchange_configuration.exchange_manager)
    return None


def get_matrix_id_from_exchange_id(exchange_name: typing.Optional[str], exchange_id: str) -> typing.Optional[str]:
    if not exchange_name:
        return None

    exchange_configurations = get_exchange_configurations_from_exchange_name(exchange_name)
    if exchange_configurations:
        for exchange_configuration in exchange_configurations.values():
            if exchange_configuration.id == exchange_id:
                return exchange_configuration.matrix_id
    return None


def get_all_exchange_ids_from_matrix_id(matrix_id) -> list:
    return [
        get_exchange_manager_id(exchange_manager)
        for exchange_manager in exchanges.Exchanges.instance().get_exchanges_managers_with_matrix_id(matrix_id)
    ]


def get_exchange_configuration_from_exchange(exchange_name: str, exchange_id: str) -> exchanges.ExchangeConfiguration:
    return exchanges.Exchanges.instance().get_exchange(exchange_name, exchange_id)


def get_all_exchange_ids_with_same_matrix_id(exchange_name: str, exchange_id: str) -> list:
    """
    Used to get all the exchange ids for the same octobot instance represented by the matrix_id
    :param exchange_name: the exchange name
    :param exchange_id: the exchange id
    :return: the exchange ids for the same matrix id
    """
    return get_all_exchange_ids_from_matrix_id(
        get_exchange_configuration_from_exchange(exchange_name, exchange_id).matrix_id)


async def register_new_pairs_on_exchange(
    exchange_name: str, matrix_id: str, pairs: list[str],
    watch_only: bool, time_frames: typing.Optional[list[commons_enums.TimeFrames]] = None
) -> None:
    for exchange_id in get_all_exchange_ids_from_matrix_id(matrix_id):
        exchange_manager = get_exchange_manager_from_exchange_id(exchange_id)
        if exchange_name == exchange_manager.exchange_name:
            await register_new_pairs_on_exchange_manager(exchange_manager, pairs, watch_only, time_frames=time_frames)
            return


async def register_new_pairs_on_exchange_manager(
    exchange_manager, pairs: list[str],
    watch_only: bool, time_frames: typing.Optional[list[commons_enums.TimeFrames]] = None
) -> None:
    if watch_only:
        await exchange_manager.exchange_config.add_watched_symbols(pairs)
    else:
        await exchange_manager.exchange_config.add_traded_symbols(pairs, time_frames or [])


def get_exchange_names() -> list:
    return exchanges.Exchanges.instance().get_exchange_names()


def get_exchange_ids() -> list:
    return exchanges.Exchanges.instance().get_exchange_ids()


def get_exchange_name(exchange_manager) -> str:
    return exchange_manager.get_exchange_name()


def get_exchange_type(exchange_manager) -> octobot_trading.enums.ExchangeTypes:
    return exchanges.get_exchange_type(exchange_manager)


def has_only_ohlcv(exchange_importers):
    return exchanges.ExchangeSimulatorConnector.get_real_available_data(exchange_importers) == \
           set(exchange_data.SIMULATOR_PRODUCERS_TO_POSSIBLE_DATA_TYPE[octobot_trading.constants.OHLCV_CHANNEL])


def get_is_backtesting(exchange_manager) -> bool:
    return exchange_manager.is_backtesting


def get_backtesting_data_files(exchange_manager) -> list:
    if not get_is_backtesting(exchange_manager):
        raise RuntimeError("Require a backtesting exchange manager")
    return exchange_manager.exchange.get_backtesting_data_files()


def get_backtesting_data_file(exchange_manager, symbol, time_frame) -> str:
    if not get_is_backtesting(exchange_manager):
        raise RuntimeError("Require a backtesting exchange manager")
    return backtesting_api.get_data_file_from_importers(
        exchange_manager.exchange.connector.exchange_importers, symbol, time_frame
    )


def get_has_websocket(exchange_manager) -> bool:
    return exchange_manager.has_websocket


def get_has_reached_websocket_limit(exchange_manager) -> bool:
    return (
        exchange_manager.exchange_web_socket
        and exchange_manager.exchange_web_socket.is_beyond_feed_exchange_limit
    )


def supports_websockets(exchange_name: str, tentacles_setup_config) -> bool:
    return exchanges.supports_websocket(exchange_name, tentacles_setup_config)


def get_trading_pairs(exchange_manager) -> list[str]:
    return exchange_manager.exchange_config.traded_symbol_pairs


def get_all_exchange_symbols(exchange_manager) -> list:
    return exchange_manager.client_symbols


def get_all_exchange_time_frames(exchange_manager) -> list:
    return exchange_manager.client_time_frames


def get_trading_symbols(exchange_manager, include_additional_pairs: bool = False) -> list[commons_symbols.Symbol]:
    if include_additional_pairs:
        return exchange_manager.exchange_config.traded_symbols + exchange_manager.exchange_config.additional_traded_pairs
    else:
        return exchange_manager.exchange_config.traded_symbols


def get_trading_timeframes(exchange_manager) -> list:
    return exchange_manager.exchange_config.traded_time_frames


def get_watched_timeframes(exchange_manager) -> list:
    return exchange_manager.exchange_config.available_time_frames


def get_relevant_time_frames(exchange_manager) -> list:
    return exchange_manager.exchange_config.get_relevant_time_frames()


def get_base_currency(exchange_manager, pair) -> str:
    return exchange_manager.exchange.get_pair_cryptocurrency(pair)


def get_fees(exchange_manager, symbol) -> dict:
    return exchange_manager.exchange.get_fees(symbol)


def get_max_handled_pair_with_time_frame(exchange_manager) -> int:
    if get_has_reached_websocket_limit(exchange_manager):
        return exchange_manager.exchange_web_socket.get_connector_max_handled_feeds()
    return exchange_manager.exchange.get_max_handled_pair_with_time_frame()


def get_currently_handled_pair_with_time_frame(exchange_manager) -> int:
    if get_has_reached_websocket_limit(exchange_manager):
        return exchange_manager.exchange_web_socket.get_connector_feeds_count()
    return exchange_manager.get_currently_handled_pair_with_time_frame()


def get_required_historical_candles_count(exchange_manager) -> int:
    return exchange_manager.exchange_config.required_historical_candles_count \
        if exchange_manager.exchange_config.required_historical_candles_count > \
        octobot_trading.constants.DEFAULT_CANDLE_HISTORY_SIZE else octobot_trading.constants.DEFAULT_CANDLE_HISTORY_SIZE


def is_overloaded(exchange_manager) -> bool:
    return exchange_manager.get_is_overloaded()


async def is_compatible_account(exchange_name: str, exchange_config: dict, tentacles_setup_config, is_sandboxed: bool) \
        -> typing.Tuple[bool, bool, str]:
    return await exchanges.is_compatible_account(exchange_name, exchange_config, tentacles_setup_config, is_sandboxed)


@contextlib.asynccontextmanager
async def get_new_ccxt_client(exchange_name: str, exchange_config: dict, tentacles_setup_config, is_sandboxed: bool):
    async with exchanges.get_local_exchange_manager(
        exchange_name, exchange_config, tentacles_setup_config, is_sandboxed, ignore_config=True
    ) as local_exchange_manager:
        yield local_exchange_manager.exchange.connector.client


def get_default_exchange_type(exchange_name: str) -> str:
    return exchanges.get_default_exchange_type(exchange_name)


def is_sponsoring(exchange_name: str) -> bool:
    return trading_backend.is_sponsoring(exchange_name)


def is_broker_enabled(exchange_manager) -> bool:
    return exchange_manager.is_broker_enabled


def get_historical_ohlcv(
        exchange_manager, symbol, time_frame, start_time, end_time,
        request_retry_timeout=octobot_trading.constants.HISTORICAL_CANDLES_FETCH_DEFAULT_TIMEOUT
):
    return exchanges.get_historical_ohlcv(
        exchange_manager, symbol, time_frame, start_time, end_time, request_retry_timeout=request_retry_timeout
    )


def get_bot_id(exchange_manager):
    return exchange_manager.bot_id


def get_supported_exchange_types(exchange_name, tentacles_setup_config) -> list:
    return exchanges.get_supported_exchange_types(exchange_name, tentacles_setup_config)


async def store_history_in_run_storage(exchange_manager):
    await exchange_manager.storage_manager.store_history()


def get_enabled_exchanges_names(config) -> list:
    return exchanges.get_enabled_exchanges(config)


def get_auto_filled_exchange_names(tentacles_setup_config) -> list:
    return exchanges.get_auto_filled_exchange_names(tentacles_setup_config)


def supports_custom_limit_order_book_fetch(exchange_manager) -> bool:
    return exchange_manager.exchange.SUPPORTS_CUSTOM_LIMIT_ORDER_BOOK_FETCH


async def get_exchange_details(
    exchange_name, is_autofilled, tentacles_setup_config, aiohttp_session
) -> exchanges.ExchangeDetails:
    return await exchanges.get_exchange_details(
        exchange_name, is_autofilled, tentacles_setup_config, aiohttp_session
    )


def cancel_ccxt_throttle_task():
    for task in asyncio.all_tasks():
        # manually cancel ccxt async throttle task since it apparently can't be cancelled otherwise
        if str(task._coro).startswith("<coroutine object Throttler.looper at"):
            task.cancel()
