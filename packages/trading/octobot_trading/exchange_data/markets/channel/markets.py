#  Drakkar-Software OctoBot-Trading
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
import asyncio

import octobot_trading.exchange_channel as exchanges_channel


class MarketsProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, markets):
        await self.perform(markets)

    async def perform(self, markets):
        try:
            await self.send(markets)
        except KeyError:
            pass
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, data):
        for consumer in self.channel.get_filtered_consumers():
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "markets": data
            })


class MarketsChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = MarketsProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer
