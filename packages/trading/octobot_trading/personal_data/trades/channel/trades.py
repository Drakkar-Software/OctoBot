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

import async_channel.constants as channel_constants

import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.enums as enums


class TradesProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, trades, old_trade=False):
        await self.perform(trades, old_trade=old_trade)

    async def perform(self, trades, old_trade=False):
        try:
            for trade in trades:
                if not trade:
                    continue
                symbol: str = self.channel.exchange_manager.get_exchange_symbol(
                    trade[enums.ExchangeConstantsOrderColumns.SYMBOL.value])
                if self.channel.get_filtered_consumers(symbol=channel_constants.CHANNEL_WILDCARD) or \
                        self.channel.get_filtered_consumers(symbol=symbol):
                    trade_id: str = trade[enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]

                    await self.channel.exchange_manager.exchange_personal_data.handle_trade_update(
                        symbol,
                        trade_id,
                        trade,
                        is_old_trade=old_trade,
                        should_notify=True)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, cryptocurrency, symbol, trade, old_trade=False):
        for consumer in self.channel.get_filtered_consumers(symbol=symbol):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "trade": trade,
                "old_trade": old_trade
            })


class TradesChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = TradesProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer
