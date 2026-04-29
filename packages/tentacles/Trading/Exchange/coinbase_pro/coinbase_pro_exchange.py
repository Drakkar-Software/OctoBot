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

import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges


class CoinbasePro(exchanges.RestExchange):
    MAX_PAGINATION_LIMIT: int = 100  # value from https://docs.pro.coinbase.com/#pagination

    FIX_MARKET_STATUS = True

    @classmethod
    def get_name(cls):
        return 'coinbasepro'

    def get_adapter_class(self):
        return CoinbaseProCCXTAdapter

    async def get_my_recent_trades(self, symbol=None, since=None, limit=None, **kwargs):
        return self._uniformize_trades(await super().get_my_recent_trades(symbol=symbol,
                                                                          since=since,
                                                                          limit=self._fix_limit(limit),
                                                                          **kwargs))

    async def get_open_orders(self, symbol=None, since=None, limit=None, **kwargs) -> list:
        return await super().get_open_orders(symbol=symbol,
                                             since=since,
                                             limit=self._fix_limit(limit),
                                             **kwargs)

    async def get_closed_orders(self, symbol=None, since=None, limit=None, **kwargs) -> list:
        return await super().get_closed_orders(symbol=symbol,
                                               since=since,
                                               limit=self._fix_limit(limit),
                                               **kwargs)

    def _fix_limit(self, limit: int) -> int:
        return min(self.MAX_PAGINATION_LIMIT, limit) if limit else limit

    def _uniformize_trades(self, trades):
        if not trades:
            return []
        for trade in trades:
            trade[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = trading_enums.OrderStatus.CLOSED.value
            trade[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value] = trade[
                trading_enums.ExchangeConstantsOrderColumns.ORDER.value
            ]
            trade[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = trading_enums.TradeOrderType.MARKET.value \
                if trade["takerOrMaker"] == trading_enums.ExchangeConstantsMarketPropertyColumns.TAKER.value \
                else trading_enums.TradeOrderType.LIMIT.value
        return trades


class CoinbaseProCCXTAdapter(exchanges.CCXTAdapter):

    def fix_trades(self, raw, **kwargs):
        raw = super().fix_trades(raw, **kwargs)
        for trade in raw:
            trade[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = trading_enums.OrderStatus.CLOSED.value
        return raw
