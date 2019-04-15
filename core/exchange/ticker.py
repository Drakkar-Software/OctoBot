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

from core.consumers_producers.consumer import ExchangeConsumer
from core.consumers_producers.consumer_producers import ConsumerProducers
from core.consumers_producers.producers import ExchangeProducer


class TickerConsumerProducers(ConsumerProducers):
    def __init__(self, exchange):
        super().__init__()
        self.exchange = exchange
        self.consumer = TickerConsumer(exchange, self)

    def subscribe_to_producer(self, consumer, symbol=None):
        if symbol not in self.producers:
            self.producers[symbol] = TickerProducer(self.exchange)

        self.producers[symbol].add_consumer(consumer)


class TickerProducer(ExchangeProducer):
    def __init__(self, exchange):
        super().__init__(exchange)

    async def receive(self):
        await self.perform()

    async def perform(self):
        await self.send(True)  # TODO


class TickerConsumer(ExchangeConsumer):
    SYMBOL = "SYMBOL"
    TICKER = "TICKER"

    def __init__(self, exchange, ticker: TickerConsumerProducers):
        super().__init__(exchange)
        self.ticker: TickerConsumerProducers = ticker

    async def perform(self, symbol, ticker):
        try:
            if symbol in self.ticker.producers:  # and price_ticker_is_initialized
                self.exchange.get_symbol_data_from_pair(symbol).update_symbol_price_ticker(ticker)
                await self.ticker.producers[symbol].receive()
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def consume(self):
        while not self.should_stop:
            data = await self.queue.get()
            await self.perform(data[self.SYMBOL], data[self.TICKER])

    @staticmethod
    def create_feed(symbol, ticker):
        return {
            TickerConsumer.SYMBOL: symbol,
            TickerConsumer.TICKER: ticker
        }
