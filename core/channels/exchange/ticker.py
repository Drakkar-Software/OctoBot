#  Drakkar-Software OctoBot
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
from asyncio import CancelledError
from typing import Iterable

from core.channels import CallbackType
from core.channels.exchange.exchange_channel import ExchangeChannel
from core.consumer import Consumer
from core.producer import Producer


class TickerProducer(Producer):
    def __init__(self, channel: ExchangeChannel):
        super().__init__(channel)

    async def receive(self, symbol, ticker):
        await self.perform(symbol, ticker)

    async def perform(self, symbol, ticker):
        try:
            if symbol in self.channel.consumers[symbol]:  # and price_ticker_is_initialized
                self.channel.exchange.get_symbol_data(symbol).update_symbol_price_ticker(ticker)
                await self.send(symbol, ticker)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def send(self, symbol, ticker):
        for consumer in self.channel.get_consumers(symbol=symbol):
            await consumer.queue.put({
                "symbol": symbol,
                "ticker": ticker
            })


class TickerConsumer(Consumer):
    def __init__(self, callback: CallbackType):
        super().__init__(callback)

    async def consume(self):
        while not self.should_stop:
            data = await self.queue.get()
            self.callback(symbol=data["symbol"], ticker=data["ticker"])


class TickerChannel(ExchangeChannel):
    def __init__(self, exchange, symbol):
        super().__init__(exchange)
        self.symbol = symbol

    def get_consumers(self, symbol) -> Iterable[TickerConsumer]:
        if symbol not in self.consumers:
            self.consumers[symbol] = {}

        return self.consumers[symbol]

    def new_consumer(self, callback: CallbackType, size=0, symbol=None):
        # create dict and list if required
        self.get_consumers(symbol=symbol)

        self.consumers[symbol] = TickerConsumer(callback)
