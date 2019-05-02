# #  Drakkar-Software OctoBot
# #  Copyright (c) Drakkar-Software, All rights reserved.
# #
# #  This library is free software; you can redistribute it and/or
# #  modify it under the terms of the GNU Lesser General Public
# #  License as published by the Free Software Foundation; either
# #  version 3.0 of the License, or (at your option) any later version.
# #
# #  This library is distributed in the hope that it will be useful,
# #  but WITHOUT ANY WARRANTY; without even the implied warranty of
# #  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# #  Lesser General Public License for more details.
# #
# #  You should have received a copy of the GNU Lesser General Public
# #  License along with this library.
import asyncio

from core.channels.exchange_channel import ExchangeChannel
from core.channels.exchange.orders import OrdersProducer


class OrdersUpdater(OrdersProducer):
    ORDERS_REFRESH_TIME = 60

    def __init__(self, channel: ExchangeChannel):
        super().__init__(channel)

    async def start(self):
        while not self.should_stop:
            for pair in self.channel.exchange_manager.traded_pairs:
                await self.push(pair, await self.channel.exchange_manager.exchange_dispatcher.get_open_orders(pair))
            await asyncio.sleep(self.ORDERS_REFRESH_TIME)

# from asyncio import CancelledError
#
# from backtesting import backtesting_enabled
#
#
# class OrderUpdater(ConsumersProducer):
#     def __init__(self, exchange, recent_trades_producers):
#         super().__init__()
#         self.exchange = exchange
#         self.producer = OrderUpdaterProducer(self.exchange)
#
#         self.consumers = {
#             recent_trades_producer.symbol: OrderUpdaterConsumer(exchange, recent_trades_producer)
#             for recent_trades_producer in recent_trades_producers
#         }
#
#
# class OrderUpdaterConsumer(ExchangeConsumer):
#     def __init__(self, exchange, recent_trades_producer):
#         super().__init__(exchange)
#         self.symbol = recent_trades_producer.symbol
#         recent_trades_producer.add_consumer(self)
#
#     async def consume(self, recent_trade=None):
#         pass
#
#     @staticmethod
#     def create_feed(**kwargs):
#         pass
#
#
# class OrderUpdaterProducer(ExchangeProducer):
#     def __init__(self, exchange):
#         super().__init__(exchange)
#         self.config = self.exchange.config
#
#         self.backtesting_enabled = backtesting_enabled(self.config)
#
#     # should be called to force refresh
#     async def receive(self):
#         await self.perform()
#
#     async def start(self):
#         while self.should_stop:
#             try:
#                 await self.perform()
#             except CancelledError:
#                 self.logger.info("Update tasks cancelled.")
#             except Exception as e:
#                 self.logger.error(f"exception when triggering update: {e}")
#                 self.logger.exception(e)
#
#     async def perform(self):
#         pass
