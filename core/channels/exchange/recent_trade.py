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
from core.channels.exchange.exchange_channel import ExchangeChannel
from core.consumer import Consumer
from core.producer import Producer


class RecentTradeProducer(Producer):
    async def receive(self, symbol, recent_trade):
        await self.perform(symbol, recent_trade)

    async def perform(self, symbol, recent_trade):
        try:
            if CONFIG_WILDCARD in self.channel.consumers or symbol in self.channel.consumers:  # and symbol_data.recent_trades_are_initialized()
                self.channel.exchange_manager.get_symbol_data(symbol).add_new_recent_trades(recent_trade)
                await self.send(symbol, recent_trade)
                await self.send(CONFIG_WILDCARD, recent_trade)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def send(self, symbol, recent_trade):
        for consumer in self.channel.get_consumers(symbol=symbol):
            await consumer.queue.put({
                "symbol": symbol,
                "recent_trade": recent_trade
            })


class RecentTradeConsumer(Consumer):
    async def consume(self):
        while not self.should_stop:
            try:
                data = await self.queue.get()
                await self.callback(symbol=data["symbol"], recent_trade=data["recent_trade"])
            except Exception as e:
                self.logger.exception(f"Exception when calling callback : {e}")


class RecentTradeChannel(ExchangeChannel):
    def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, size: int = 0, symbol: str = CONFIG_WILDCARD):
        self._add_new_consumer_and_run(symbol, RecentTradeConsumer(callback, size=size))
