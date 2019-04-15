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


class OrderBookConsumerProducers(ConsumerProducers):
    def __init__(self, exchange):
        super().__init__()
        self.exchange = exchange
        self.consumer = OrderBookConsumer(exchange, self)

    def subscribe_to_producer(self, consumer, symbol=None):
        if symbol not in self.producers:
            self.producers[symbol] = OrderBookProducer(self.exchange)

        self.producers[symbol].add_consumer(consumer)


class OrderBookProducer(ExchangeProducer):
    def __init__(self, exchange):
        super().__init__(exchange)

    async def receive(self):
        await self.perform()

    async def perform(self):
        await self.send(True)  # TODO


class OrderBookConsumer(ExchangeConsumer):
    SYMBOL = "SYMBOL"
    ORDER_BOOK = "ORDER_BOOK"

    def __init__(self, exchange, order_book: OrderBookConsumerProducers):
        super().__init__(exchange)
        self.order_book: OrderBookConsumerProducers = order_book

    async def perform(self, symbol, order_book):
        try:
            if symbol in self.order_book.producers:  # and symbol_data.order_book_is_initialized()
                self.exchange.get_symbol_data_from_pair(symbol).update_order_book(order_book)
                await self.order_book.producers[symbol].receive()
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def consume(self):
        while not self.should_stop:
            data = await self.queue.get()
            await self.perform(data[self.SYMBOL], data[self.ORDER_BOOK])

    @staticmethod
    def create_feed(symbol, order_book):
        return {
            OrderBookConsumer.SYMBOL: symbol,
            OrderBookConsumer.ORDER_BOOK: order_book
        }
