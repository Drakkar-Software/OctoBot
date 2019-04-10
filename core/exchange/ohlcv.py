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

from typing import Dict

from core.consumer import ExchangeConsumer
from core.consumer_producer import ConsumerProducer
from core.producers import ExchangeProducer, Producer


class OHLCV(ConsumerProducer):
    def __init__(self, exchange):
        super().__init__()
        self.exchange = exchange
        self.producers: Dict[Producer] = {}
        self.consumer = OHLCVConsumer(exchange, self)

    def subscribe_to_producer(self, consumer, time_frame=None, symbol=None):
        if symbol not in self.producers:
            self.producers[symbol] = {}

        if time_frame not in self.producers:
            self.producers[symbol][time_frame] = OHLCVProducer(self.exchange)

        self.producers[symbol][time_frame].add_consumer(consumer)

    async def start(self):
        await self.consumer.start()
        for producer in [symbol_producer.values() for symbol_producer in self.producers.values()]:
            await producer.start()

    async def stop(self):
        await self.consumer.stop()
        for producer in [symbol_producer.values() for symbol_producer in self.producers.values()]:
            await producer.stop()

    async def run(self):
        await self.consumer.run()
        for producer in [symbol_producer.values() for symbol_producer in self.producers.values()]:
            await producer.run()


class OHLCVProducer(ExchangeProducer):
    def __init__(self, exchange):
        super().__init__(exchange)

    async def receive(self):
        await self.perform()

    async def perform(self):
        await self.send(True)  # TODO


class OHLCVConsumer(ExchangeConsumer):
    TIME_FRAME = "TIME_FRAME"
    SYMBOL = "SYMBOL"

    def __init__(self, exchange, ohlcv: OHLCV):
        super().__init__(exchange)

        self.ohlcv = ohlcv
        self.symbols = self.exchange.traded_pairs
        self.symbol_evaluators = []
        self.time_frames = []

        self.in_backtesting = False

    async def start(self):
        if self.time_frames and self.symbols:

            await self.consume()
        else:
            self.should_stop = True
            self.logger.warning("No time frames to monitor, going to sleep. "
                                "This is normal if you did not activate any technical analysis evaluator.")

    async def perform(self, time_frame, symbol):
        try:
            if symbol in self.ohlcv.producers and time_frame in self.ohlcv.producers[symbol]:
                await self.ohlcv.producers[symbol][time_frame].receive()
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def consume(self):
        while not self.should_stop:
            data = await self.queue.get()
            await self.perform(data[self.TIME_FRAME], data[self.SYMBOL])

    @staticmethod
    def create_feed(time_frame, symbol):
        return {
            OHLCVConsumer.TIME_FRAME: time_frame,
            OHLCVConsumer.SYMBOL: symbol
        }
