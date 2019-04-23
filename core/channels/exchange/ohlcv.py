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
from typing import List

from config import CONSUMER_CALLBACK_TYPE
from core.channels.exchange.exchange_channel import ExchangeChannel
from core.consumer import Consumer
from core.producer import Producer


class OHLCVProducer(Producer):
    def __init__(self, channel):
        super().__init__(channel)

    async def receive(self, time_frame, symbol, candle):
        await self.perform(symbol, time_frame, candle)

    async def perform(self, time_frame, symbol, candle):
        try:
            if symbol in self.channel.consumers and time_frame in self.channel.consumers[symbol]:
                self.channel.exchange_manager.uniformize_candles_if_necessary(candle)
                self.channel.exchange_manager.get_symbol_data(symbol).update_symbol_candles(time_frame,
                                                                                            candle,
                                                                                            replace_all=False)
                await self.send(time_frame, symbol, candle)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def send(self, time_frame, symbol, candle):
        for consumer in self.channel.get_consumers(time_frame=time_frame, symbol=symbol):
            await consumer.queue.put({
                "symbol": symbol,
                "time_frame": time_frame,
                "candle": candle
            })


class OHLCVConsumer(Consumer):
    def __init__(self, callback: CONSUMER_CALLBACK_TYPE):
        super().__init__(callback)

    async def consume(self):
        while not self.should_stop:
            data = await self.queue.get()
            self.callback(symbol=data["symbol"], time_frame=data["time_frame"], candle=data["candle"])


class OHLCVChannel(ExchangeChannel):
    def __init__(self, exchange_manager):
        super().__init__(exchange_manager)

    def get_consumers(self, time_frame, symbol) -> List:
        if symbol not in self.consumers:
            self.consumers[symbol] = {}

        if time_frame not in self.consumers[symbol]:
            self.consumers[symbol][time_frame] = []

        return self.consumers[symbol][time_frame]

    def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, size=0, time_frame=None, symbol=None):
        # create dict and list if required
        self.get_consumers(time_frame=time_frame, symbol=symbol)

        consumer = OHLCVConsumer(callback)
        self.consumers[symbol].append(consumer)
        consumer.run()
