#  Drakkar-Software OctoBot-Tentacles
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
import ccxt.pro as ccxt_pro
import octobot_trading.exchanges as exchanges
from octobot_trading.enums import WebsocketFeeds as Feeds
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
from ..hollaex.hollaex_exchange import hollaex


class HollaexCCXTWebsocketConnector(exchanges.CCXTWebsocketConnector):
    BASE_WS_API = f"{hollaex.BASE_REST_API}/stream"
    EXCHANGE_FEEDS = {
        Feeds.TRADES: Feeds.UNSUPPORTED.value,
        Feeds.KLINE: Feeds.UNSUPPORTED.value,
        Feeds.TICKER: Feeds.UNSUPPORTED.value,
        Feeds.CANDLE: Feeds.UNSUPPORTED.value,
    }

    def _create_client(self, force_unauth=False):
        if not self.additional_config:
            additional_connector_config = self.exchange_manager.exchange.get_additional_connector_config()
            try:
                self._update_urls(additional_connector_config)
                # use rest exchange additional config if any
                self.additional_config = additional_connector_config
            except KeyError as err:
                self.logger.error(f"Error when updating exchange url: {err}")
        super()._create_client()

    def _update_urls(self, additional_connector_config):
        rest_url = additional_connector_config[ccxt_enums.ExchangeColumns.URLS.value][
            ccxt_enums.ExchangeColumns.API.value
        ][ccxt_enums.ExchangeColumns.REST.value]
        if hollaex.BASE_REST_API not in rest_url:
            current_ws_url = ccxt_pro.hollaex().describe()[ccxt_enums.ExchangeColumns.URLS.value][
                ccxt_enums.ExchangeColumns.API.value
            ][ccxt_enums.ExchangeColumns.WEBSOCKET.value]
            custom_url = rest_url.split("https://")[1]
            additional_connector_config[ccxt_enums.ExchangeColumns.URLS.value][
                ccxt_enums.ExchangeColumns.API.value
            ][ccxt_enums.ExchangeColumns.WEBSOCKET.value] = current_ws_url.replace(hollaex.BASE_REST_API, custom_url)

    @classmethod
    def get_name(cls):
        return hollaex.get_name()
