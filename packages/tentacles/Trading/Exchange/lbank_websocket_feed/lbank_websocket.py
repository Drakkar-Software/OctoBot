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
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_trading.exchanges as exchanges
from octobot_trading.enums import WebsocketFeeds as Feeds
import tentacles.Trading.Exchange.lbank.lbank_exchange as lbank_exchange


class LBankCCXTWebsocketConnector(exchanges.CCXTWebsocketConnector, lbank_exchange.LBankSignConnectorMixin):
    EXCHANGE_FEEDS = {
        Feeds.TRADES: True,
        Feeds.KLINE: True,
        Feeds.TICKER: True,
        Feeds.CANDLE: True,
    }
    FIX_CANDLES_TIMEZONE_IF_NEEDED: bool = True
    # A http proxy can enable other traded pairs with can't be watched from ws
    # of no proxy is provided
    REQUIRES_PROXY_IF_REST_PROXY_ENABLED: bool = True

    def __init__(self, *args, **kwargs):
        exchanges.CCXTWebsocketConnector.__init__(self, *args, **kwargs)
        lbank_exchange.LBankSignConnectorMixin.__init__(self)

    def _create_client(self):
        exchanges.CCXTWebsocketConnector._create_client(self)
        self.client.sign = self._lazy_maybe_force_signed_requests(self.client.sign)

    def _should_authenticate(self):
        return exchanges.CCXTWebsocketConnector._should_authenticate(self) or (
            # oveerride to authenticate if the connector is authenticated
            self.exchange_manager.exchange.connector 
            and self.exchange_manager.exchange.connector.is_authenticated
        )

    @classmethod
    def get_name(cls):
        return lbank_exchange.LBank.get_name()

    def get_adapter_class(self, adapter_class):
        return lbank_exchange.LBankCCXTAdapter
