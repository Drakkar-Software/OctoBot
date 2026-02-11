# Drakkar-Software OctoBot-Trading
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
import octobot_commons.tentacles_management as tentacles_management
import octobot_commons.constants as commons_constants
import octobot_tentacles_manager.api as api
import octobot_trading.exchanges.abstract_websocket_exchange as abstract_websocket
import octobot_trading.exchanges.config.proxy_config as proxy_config_import


def force_disable_web_socket(config, exchange_name) -> bool:
    return commons_constants.CONFIG_EXCHANGE_WEB_SOCKET in config[commons_constants.CONFIG_EXCHANGES][exchange_name] \
           and not config[commons_constants.CONFIG_EXCHANGES][exchange_name][commons_constants.CONFIG_EXCHANGE_WEB_SOCKET]


def check_web_socket_config(config, exchange_name) -> bool:
    return not force_disable_web_socket(config, exchange_name)


def is_proxy_config_compatible_with_websocket_connector(
    websocket_connector_class, proxy_config: proxy_config_import.ProxyConfig
) -> bool:
    if websocket_connector_class.REQUIRES_PROXY_IF_REST_PROXY_ENABLED and (
        proxy_config.has_rest_proxy() and not proxy_config.has_websocket_proxy()
    ):
        return False
    return True


def search_websocket_class(websocket_class, exchange_manager):
    for websocket_impl_class in tentacles_management.get_all_classes_from_parent(websocket_class):
        # return websocket exchange if available
        if websocket_impl_class.has_name(exchange_manager):
            return websocket_impl_class
    return None


def supports_websocket(exchange_name, tentacles_setup_config) -> bool:
    for connector in abstract_websocket.AbstractWebsocketExchange.__subclasses__():
        try:
            if api.get_class_from_name_with_activated_required_tentacles(
                name=exchange_name,
                tentacles_setup_config=tentacles_setup_config,
                parent_class=connector
            ) is not None:
                return True
        except NotImplementedError:
            pass
    return False
