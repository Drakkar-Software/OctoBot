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


class RecentTradeConsumerProducers(ConsumerProducers):
    def __init__(self, exchange):
        super().__init__()
        self.exchange = exchange
        self.consumer = RecentTradeConsumer(exchange, self)

    def subscribe_to_producer(self, consumer, symbol=None):
        if symbol not in self.producers:
            self.producers[symbol] = RecentTradeProducer(self.exchange, symbol)

        self.producers[symbol].add_consumer(consumer)


class RecentTradeProducer(ExchangeProducer):
    def __init__(self, exchange, symbol):
        super().__init__(exchange)
        self.symbol = symbol

    async def receive(self, recent_trade):
        await self.perform(recent_trade)

    async def perform(self, recent_trade):
        await super().send(recent_trade=recent_trade)


class RecentTradeConsumer(ExchangeConsumer):
    SYMBOL = "SYMBOL"
    RECENT_TRADE = "RECENT_TRADE"

    def __init__(self, exchange, recent_trade: RecentTradeConsumerProducers):
        super().__init__(exchange)
        self.recent_trade: RecentTradeConsumerProducers = recent_trade

    async def perform(self, symbol, recent_trade):
        try:
            if symbol in self.recent_trade.producers:  # and symbol_data.recent_trades_are_initialized()
                self.exchange.get_symbol_data_from_pair(symbol).add_new_recent_trades(recent_trade)
                await self.recent_trade.producers[symbol].receive(symbol, recent_trade)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def consume(self):
        while not self.should_stop:
            data = await self.queue.get()
            await self.perform(data[self.SYMBOL], data[self.RECENT_TRADE])

    @staticmethod
    def create_feed(symbol, recent_trade):
        return {
            RecentTradeConsumer.SYMBOL: symbol,
            RecentTradeConsumer.RECENT_TRADE: recent_trade
        }
