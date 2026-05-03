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
import asyncio
import decimal
import typing

import octobot_trading.exchanges as exchanges
import octobot_trading.enums as trading_enums


class Phemex(exchanges.RestExchange):
    ALLOWED_OHLCV_LIMITS = [5, 10, 50, 100, 500, 1000]

    @classmethod
    def get_name(cls):
        return 'phemex'

    def _get_adapted_limit(self, limit):
        prev = self.ALLOWED_OHLCV_LIMITS[0]
        for adapted in self.ALLOWED_OHLCV_LIMITS:
            if adapted > limit:
                return prev
            prev = adapted
        return prev

    async def get_symbol_prices(self, symbol, time_frame, limit: int = 500, **kwargs: dict):
        if limit not in self.ALLOWED_OHLCV_LIMITS:
            limit = self._get_adapted_limit(limit)
        return await super().get_symbol_prices(symbol, time_frame, limit=limit, **kwargs)

    async def create_order(self, order_type: trading_enums.TraderOrderType, symbol: str, quantity: decimal.Decimal,
                           price: decimal.Decimal = None, stop_price: decimal.Decimal = None,
                           side: trading_enums.TradeOrderSide = None, current_price: decimal.Decimal = None,
                           reduce_only: bool = False, params: dict = None) -> typing.Optional[dict]:
        if order_type is trading_enums.TraderOrderType.BUY_MARKET \
                or order_type is trading_enums.TraderOrderType.SELL_MARKET:
            # remove price argument on market orders or ccxt will try to convert cost into amount and
            # make rounding differences
            price = None
        return await super().create_order(order_type, symbol, quantity,
                                          price=price, stop_price=stop_price,
                                          side=side, current_price=current_price,
                                          reduce_only=reduce_only, params=params)

    async def cancel_order(
            self, exchange_order_id: str, symbol: str, order_type: trading_enums.TraderOrderType, **kwargs: dict
    ) -> trading_enums.OrderStatus:
        order_status = await super().cancel_order(exchange_order_id, symbol, order_type, **kwargs)
        if order_status == trading_enums.OrderStatus.PENDING_CANCEL:
            # cancelled orders can't be fetched, consider as cancelled
            order_status = trading_enums.OrderStatus.CANCELED
        return order_status

    async def get_order(
        self,
        exchange_order_id: str,
        symbol: typing.Optional[str] = None,
        order_type: typing.Optional[trading_enums.TraderOrderType] = None,
        **kwargs: dict
    ) -> dict:
        if order := await self.connector.get_order(
            symbol=symbol, exchange_order_id=exchange_order_id, order_type=order_type, **kwargs
        ):
            return order
        # try from closed orders (get_order is not returning filled or cancelled orders)
        if order := await self.get_order_from_open_and_closed_orders(exchange_order_id, symbol):
            return order
        # try from trades (get_order is not returning filled or cancelled orders)
        return await self._get_order_from_trades(symbol, exchange_order_id, {})

    async def _get_order_from_trades(self, symbol, exchange_order_id, order_to_update):
        # usually the last trade is the right one
        for _ in range(3):
            if (order := await self.get_order_from_trades(symbol, exchange_order_id, order_to_update)) is None:
                await asyncio.sleep(3)
            else:
                return order
        return None
