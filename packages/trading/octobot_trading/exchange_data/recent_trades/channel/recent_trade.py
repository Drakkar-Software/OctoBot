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


class RecentTradeProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, symbol, recent_trades, replace_all=False):
        await self.perform(symbol, recent_trades, replace_all=replace_all)

    async def perform(self, symbol, recent_trades, replace_all=False):
        try:
            if self.channel.get_filtered_consumers(symbol=constants.CHANNEL_WILDCARD) or \
                    self.channel.get_filtered_consumers(symbol=symbol):
                recent_trades = self.channel.exchange_manager.get_symbol_data(symbol).handle_recent_trade_update(
                    recent_trades,
                    replace_all=replace_all)

                if recent_trades:
                    await self.send(cryptocurrency=self.channel.exchange_manager.exchange.
                                    get_pair_cryptocurrency(symbol),
                                    symbol=symbol,
                                    recent_trades=recent_trades)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, cryptocurrency, symbol, recent_trades):
        for consumer in self.channel.get_filtered_consumers(symbol=symbol):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "recent_trades": recent_trades
            })


class RecentTradeChannel(exchanges_channel.ExchangeChannel):
    FILTER_SIZE = 10
    PRODUCER_CLASS = RecentTradeProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer


class LiquidationsProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, symbol, liquidations):
        await self.perform(symbol, liquidations)

    async def perform(self, symbol, liquidations):
        try:
            if self.channel.get_filtered_consumers(symbol=constants.CHANNEL_WILDCARD) or \
                    self.channel.get_filtered_consumers(symbol=symbol):
                self.channel.exchange_manager.get_symbol_data(symbol).handle_liquidations(liquidations)
                await self.send(cryptocurrency=self.channel.exchange_manager.exchange.get_pair_cryptocurrency(symbol),
                                symbol=symbol,
                                liquidations=liquidations)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, cryptocurrency, symbol, liquidations):
        for consumer in self.channel.get_filtered_consumers(symbol=symbol):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "liquidations": liquidations
            })


class LiquidationsChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = LiquidationsProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer
