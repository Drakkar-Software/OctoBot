#  Drakkar-Software OctoBot-Private-Tentacles
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
import typing

import octobot_commons.enums
import octobot_commons.constants
import octobot_trading.exchanges as exchanges
import octobot_trading.enums as trading_enums


class Bitfinex(exchanges.RestExchange):

    # bitfinex only supports 1, 25 and 100 size
    # https://docs.bitfinex.com/reference#rest-public-book
    SUPPORTED_ORDER_BOOK_LIMITS = [1, 25, 100]
    DEFAULT_ORDER_BOOK_LIMIT = 25
    DEFAULT_CANDLE_LIMIT = 500

    @classmethod
    def get_name(cls):
        return 'bitfinex'

    def get_adapter_class(self):
        return BitfinexCCXTAdapter

    async def get_symbol_prices(self, symbol, time_frame, limit: int = 500, **kwargs: dict):
        if "since" not in kwargs:
            # prevent bitfinex from getting candles from 2014
            tf_seconds = octobot_commons.enums.TimeFramesMinutes[time_frame] * \
                octobot_commons.constants.MINUTE_TO_SECONDS
            kwargs["since"] = (self.get_exchange_current_time() - tf_seconds * limit) \
                * octobot_commons.constants.MSECONDS_TO_SECONDS
        return await super().get_symbol_prices(symbol, time_frame, limit=limit, **kwargs)

    async def get_kline_price(self, symbol: str, time_frame: octobot_commons.enums.TimeFrames,
                              **kwargs: dict) -> typing.Optional[list]:
        return (await self.get_symbol_prices(symbol, time_frame, limit=1))[-1:]

    async def get_order_book(self, symbol, limit=DEFAULT_ORDER_BOOK_LIMIT, **kwargs):
        if limit is None or limit not in self.SUPPORTED_ORDER_BOOK_LIMITS:
            self.logger.debug(f"Trying to get_order_book with limit not {self.SUPPORTED_ORDER_BOOK_LIMITS} : ({limit})")
            limit = self.DEFAULT_ORDER_BOOK_LIMIT
        return await super().get_recent_trades(symbol=symbol, limit=limit, **kwargs)


class BitfinexCCXTAdapter(exchanges.CCXTAdapter):

    def fix_ticker(self, raw, **kwargs):
        fixed = super().fix_ticker(raw, **kwargs)
        fixed[trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value] = \
            fixed.get(trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value) or self.connector.client.seconds()
        return fixed
