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


class OHLCVConsumerProducers(ConsumerProducers):
    def __init__(self, exchange):
        super().__init__()
        self.exchange = exchange
        self.consumer = OHLCVConsumer(exchange, self)

    def subscribe_to_producer(self, consumer, time_frame=None, symbol=None):
        if symbol not in self.producers:
            self.producers[symbol] = {}

        if time_frame not in self.producers:
            self.producers[symbol][time_frame] = OHLCVProducer(self.exchange)

        self.producers[symbol][time_frame].add_consumer(consumer)


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
    OHLCV = "OHLCV"

    def __init__(self, exchange, ohlcv: OHLCVConsumerProducers):
        super().__init__(exchange)
        self.ohlcv = ohlcv

    async def perform(self, time_frame, symbol, candle):
        try:
            if symbol in self.ohlcv.producers and time_frame in self.ohlcv.producers[symbol]:
                self.exchange.uniformize_candles_if_necessary(candle)
                self.exchange.get_symbol_data_from_pair(symbol).update_symbol_candles(time_frame,
                                                                                      candle,
                                                                                      replace_all=False)
                await self.ohlcv.producers[symbol][time_frame].receive()
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def consume(self):
        while not self.should_stop:
            data = await self.queue.get()
            await self.perform(data[self.TIME_FRAME], data[self.SYMBOL], data[self.OHLCV])

    @staticmethod
    def create_feed(time_frame, symbol, candle):
        return {
            OHLCVConsumer.TIME_FRAME: time_frame,
            OHLCVConsumer.SYMBOL: symbol,
            OHLCVConsumer.OHLCV: candle
        }
