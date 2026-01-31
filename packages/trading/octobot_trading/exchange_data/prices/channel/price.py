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


class MarkPriceProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, symbol, mark_price, mark_price_source=enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value):
        await self.perform(symbol, mark_price, mark_price_source=mark_price_source)

    async def perform(self, symbol, mark_price, mark_price_source=enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value):
        try:
            if self.channel.get_filtered_consumers(symbol=channel_constants.CHANNEL_WILDCARD) or \
                    self.channel.get_filtered_consumers(symbol=symbol):
                if self.channel.exchange_manager.get_symbol_data(symbol).handle_mark_price_update(mark_price,
                                                                                                  mark_price_source):
                    # only send mark price if price got updated
                    # mark_price attribute access required to send calculation result
                    await self.send(cryptocurrency=self.channel.exchange_manager.exchange.get_pair_cryptocurrency(
                                        symbol),
                                    symbol=symbol,
                                    mark_price=self.channel.exchange_manager.get_symbol_data(
                                        symbol).prices_manager.mark_price)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, cryptocurrency, symbol, mark_price):
        for consumer in self.channel.get_filtered_consumers(symbol=symbol):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "mark_price": mark_price
            })


class MarkPriceChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = MarkPriceProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer
