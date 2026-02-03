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

import octobot_trading.exchanges.connectors.ccxt.ccxt_websocket_connector as ccxt_websocket_connector
import octobot_trading.exchanges.types as exchanges_types
import octobot_tentacles_manager.api as api


class DefaultWebSocketExchange(exchanges_types.WebSocketExchange):
    DEFAULT_CONNECTOR_CLASS = ccxt_websocket_connector.CCXTWebsocketConnector

    @classmethod
    def get_exchange_connector_class(cls, exchange_manager):
        return api.get_class_from_name_with_activated_required_tentacles(
            name=exchange_manager.exchange.get_associated_websocket_exchange_name(),
            tentacles_setup_config=exchange_manager.tentacles_setup_config,
            parent_class=cls.DEFAULT_CONNECTOR_CLASS
        )

    def create_feeds(self):
        try:
            connector = self.websocket_connector(
                config=self.config,
                exchange_manager=self.exchange_manager,
                websocket_name=self.websocket_connector.get_name()
            )
            connector.initialize(pairs=self.pairs, time_frames=self.time_frames, channels=self.channels)
            self.websocket_connectors.append(connector)

        except ValueError as e:
            self.logger.exception(e, True, f"Fail to create feed : {e}")
