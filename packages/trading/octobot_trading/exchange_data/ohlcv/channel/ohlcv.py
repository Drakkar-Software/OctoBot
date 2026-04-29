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

import async_channel.constants as constants

import octobot_trading.exchange_channel as exchanges_channel


class OHLCVProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, time_frame, symbol, candle, replace_all=False, partial=False):
        await self.perform(time_frame, symbol, candle, replace_all, partial)

    async def perform(self, time_frame, symbol, candle, replace_all=False, partial=False):
        try:
            if self.channel.get_filtered_consumers(symbol=constants.CHANNEL_WILDCARD) or \
                    self.channel.get_filtered_consumers(symbol=symbol, time_frame=time_frame.value):
                await self.channel.exchange_manager.get_symbol_data(symbol) \
                    .handle_candles_update(time_frame, candle, replace_all=replace_all, partial=partial, upsert=False)
                if candle and (partial or replace_all):
                    candle = candle[-1]
                await self.send(cryptocurrency=self.channel.exchange_manager.exchange.
                                get_pair_cryptocurrency(symbol),
                                time_frame=time_frame.value,
                                symbol=symbol,
                                candle=candle)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, cryptocurrency, symbol, time_frame, candle):
        for consumer in self.channel.get_filtered_consumers(symbol=symbol, time_frame=time_frame):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "time_frame": time_frame,
                "candle": candle
            })


class OHLCVChannel(exchanges_channel.TimeFrameExchangeChannel):
    PRODUCER_CLASS = OHLCVProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer
