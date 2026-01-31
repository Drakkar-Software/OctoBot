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


class OrderBookProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, symbol, asks, bids, update_order_book=True):
        await self.perform(symbol, asks, bids, update_order_book)

    async def perform(self, symbol, asks, bids, update_order_book):
        try:
            if self.channel.get_filtered_consumers(symbol=constants.CHANNEL_WILDCARD) or \
                    self.channel.get_filtered_consumers(symbol=symbol):
                if update_order_book:
                    self.channel.exchange_manager.get_symbol_data(symbol).handle_order_book_update(asks, bids)
                await self.send(cryptocurrency=self.channel.exchange_manager.exchange.
                                get_pair_cryptocurrency(symbol),
                                symbol=symbol,
                                asks=asks,
                                bids=bids)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, cryptocurrency, symbol, asks, bids):
        for consumer in self.channel.get_filtered_consumers(symbol=symbol):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "asks": asks,
                "bids": bids
            })


class OrderBookChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = OrderBookProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer


class OrderBookTickerProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, symbol, ask_quantity, ask_price, bid_quantity, bid_price):
        await self.perform(symbol, ask_quantity, ask_price, bid_quantity, bid_price)

    async def perform(self, symbol, ask_quantity, ask_price, bid_quantity, bid_price):
        try:
            if self.channel.get_filtered_consumers(symbol=constants.CHANNEL_WILDCARD) or \
                    self.channel.get_filtered_consumers(symbol=symbol):
                self.channel.exchange_manager.get_symbol_data(symbol).handle_order_book_ticker_update(ask_quantity,
                                                                                                      ask_price,
                                                                                                      bid_quantity,
                                                                                                      bid_price)
                await self.send(cryptocurrency=self.channel.exchange_manager.exchange.
                                get_pair_cryptocurrency(symbol),
                                symbol=symbol,
                                ask_quantity=ask_quantity, ask_price=ask_price,
                                bid_quantity=bid_quantity, bid_price=bid_price)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, cryptocurrency, symbol, ask_quantity, ask_price, bid_quantity, bid_price):
        for consumer in self.channel.get_filtered_consumers(symbol=symbol):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "ask_quantity": ask_quantity,
                "ask_price": ask_price,
                "bid_quantity": bid_quantity,
                "bid_price": bid_price
            })


class OrderBookTickerChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = OrderBookTickerProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer
