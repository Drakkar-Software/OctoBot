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
import octobot_trading.exchanges as exchanges
from octobot_trading.enums import WebsocketFeeds as Feeds
import tentacles.Trading.Exchange.coinbase.coinbase_exchange as coinbase_exchange


class CoinbaseCCXTWebsocketConnector(exchanges.CCXTWebsocketConnector):
    EXCHANGE_FEEDS = {
        Feeds.TRADES: True,
        Feeds.KLINE: Feeds.UNSUPPORTED.value,
        Feeds.TICKER: True,
        Feeds.CANDLE: Feeds.UNSUPPORTED.value,
    }

    @classmethod
    def get_name(cls):
        return coinbase_exchange.Coinbase.get_name()

    def _get_keys_adapter(self):
        return self.exchange_manager.exchange.connector._keys_adapter

    def get_adapter_class(self, adapter_class):
        return coinbase_exchange.CoinbaseCCXTAdapter
