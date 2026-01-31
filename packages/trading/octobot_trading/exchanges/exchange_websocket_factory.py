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
import octobot_trading.constants
import octobot_trading.exchanges as exchanges


def is_channel_managed_by_websocket(exchange_manager, channel):
    return (
        not exchange_manager.rest_only
        and exchange_manager.has_websocket
        and not exchange_manager.is_backtesting
        and channel in octobot_trading.constants.WEBSOCKET_FEEDS_TO_TRADING_CHANNELS
        and exchange_manager.exchange_web_socket is not None
        and any([
            exchange_manager.exchange_web_socket.is_feed_available(feed)
            for feed in octobot_trading.constants.WEBSOCKET_FEEDS_TO_TRADING_CHANNELS[channel]
        ])
    )


def is_channel_fully_managed_by_websocket(exchange_manager, channel):
    return (
        (
            channel not in octobot_trading.constants.ALWAYS_STARTED_REST_PRODUCER_CHANNELS
        ) and (
            not any([
                # no associated feed is related to a time frame
                exchange_manager.exchange_web_socket.is_time_frame_related_feed(feed)
                for feed in octobot_trading.constants.WEBSOCKET_FEEDS_TO_TRADING_CHANNELS[channel]
            ])
            or all([
                # all required time frames are supported
                exchange_manager.exchange_web_socket.is_time_frame_supported(time_frame)
                for time_frame in exchange_manager.exchange_config.available_time_frames
            ])
        )
    )


def is_websocket_feed_requiring_init(exchange_manager, channel):
    return any([exchange_manager.exchange_web_socket.is_feed_requiring_init(feed)
                for feed in octobot_trading.constants.WEBSOCKET_FEEDS_TO_TRADING_CHANNELS[channel]])


async def search_and_create_websocket(exchange_manager):
    ws_exchange_class = exchanges.search_websocket_class(exchanges.WebSocketExchange, exchange_manager)
    if ws_exchange_class is not None:
        await _create_websocket(exchange_manager, exchanges.WebSocketExchange.__name__, ws_exchange_class)


async def _create_websocket(exchange_manager, websocket_class_name, ws_exchange_class):
    try:
        exchange_manager.exchange_web_socket = ws_exchange_class(exchange_manager.config, exchange_manager)
        await _init_websocket(exchange_manager)
        if exchange_manager.exchange_web_socket.is_websocket_running:
            exchange_manager.logger.info(
                f"{ws_exchange_class.get_name()} connecting to {exchange_manager.exchange.name.capitalize()}"
            )
        else:
            exchange_manager.has_websocket = False
    except Exception as e:
        exchange_manager.logger.error(f"Fail to init websocket for {websocket_class_name} "
                                      f"({exchange_manager.exchange.name}): {e}")
        exchange_manager.exchange_web_socket = None
        exchange_manager.has_websocket = False
        raise e


async def _init_websocket(exchange_manager):
    await exchange_manager.exchange_web_socket.init_websocket(exchange_manager.exchange_config.available_time_frames,
                                                              exchange_manager.exchange_config.traded_symbol_pairs,
                                                              exchange_manager.tentacles_setup_config)

    await exchange_manager.exchange_web_socket.start_sockets()

    exchange_manager.has_websocket = exchange_manager.exchange_web_socket.is_websocket_running
