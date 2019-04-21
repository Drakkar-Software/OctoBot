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

from core.channels.factories.producers_channel import ProducersChannel
from core.consumer import Consumer
from core.producer import Producer


class OHLCVProducer(Producer):
    def __init__(self):
        super().__init__()

    async def receive(self):
        await self.perform()

    async def perform(self):
        await self.send()  # TODO


class OHLCVConsumer(Consumer):
    def __init__(self, queue, ohlcv):
        super().__init__(queue)
        self.ohlcv = ohlcv

    async def perform(self, time_frame, symbol, candle):
        try:
            if symbol in self.ohlcv.producers and time_frame in self.ohlcv.producers[symbol]:
                self.ohlcv.exchange.uniformize_candles_if_necessary(candle)
                self.ohlcv.exchange.get_symbol_data(symbol).update_symbol_candles(time_frame,
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
            await self.perform(data["pair"],
                               data["time_frame"],
                               data["candle"])


class OHLCVChannel(ProducersChannel):
    def __init__(self, exchange):
        super().__init__()
        self.exchange = exchange

    def new_consumer(self, time_frame=None, symbol=None) -> OHLCVConsumer:
        if symbol not in self.producers:
            self.producers[symbol] = {}

        if time_frame not in self.producers:
            self.producers[symbol][time_frame] = OHLCVProducer()

        return OHLCVConsumer(self.producers[symbol][time_frame].new_consumer(), self)
