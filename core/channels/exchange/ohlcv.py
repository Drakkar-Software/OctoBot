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

from config import CONSUMER_CALLBACK_TYPE, CONFIG_WILDCARD
from core.channels.exchange_channel import ExchangeChannel
from core.consumer import Consumer
from core.producer import Producer


class OHLCVProducer(Producer):
    async def push(self, time_frame, symbol, candle):
        await self.perform(symbol, time_frame, candle)

    async def perform(self, time_frame, symbol, candle):
        try:
            # TODO manage wildcard
            if symbol in self.channel.consumers and time_frame in self.channel.consumers[symbol]:
                self.channel.exchange_manager.uniformize_candles_if_necessary(candle)
                self.channel.exchange_manager.get_symbol_data(symbol).update_symbol_candles(time_frame,
                                                                                            candle,
                                                                                            replace_all=False)
                await self.send(time_frame, symbol, candle)

            if CONFIG_WILDCARD in self.channel.consumers and time_frame in self.channel.consumers[CONFIG_WILDCARD]:
                await self.send(time_frame, CONFIG_WILDCARD, candle)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def send(self, time_frame, symbol, candle):
        for consumer in self.channel.get_consumers_by_timeframe(symbol=symbol, time_frame=time_frame):
            await consumer.queue.put({
                "symbol": symbol,
                "time_frame": time_frame,
                "candle": candle
            })


class OHLCVConsumer(Consumer):
    async def consume(self):
        while not self.should_stop:
            try:
                data = await self.queue.get()
                await self.callback(symbol=data["symbol"], time_frame=data["time_frame"], candle=data["candle"])
            except Exception as e:
                self.logger.exception(f"Exception when calling callback : {e}")


class OHLCVChannel(ExchangeChannel):
    def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, size=0, symbol=CONFIG_WILDCARD, time_frame=None):
        self._add_new_consumer_and_run(OHLCVConsumer(callback, size=size), symbol=symbol, time_frame=time_frame)
