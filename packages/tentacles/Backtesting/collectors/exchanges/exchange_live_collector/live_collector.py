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
import asyncio
import logging
import time

import octobot_backtesting.collectors.exchanges as exchanges
import octobot_commons.channels_name as channels_name
import tentacles.Backtesting.importers.exchanges.generic_exchange_importer as generic_exchange_importer

try:
    import octobot_trading.exchange_channel as exchange_channel
    import octobot_trading.api as trading_api
except ImportError:
    logging.error("ExchangeLiveDataCollector requires OctoBot-Trading package installed")


class ExchangeLiveDataCollector(exchanges.AbstractExchangeLiveCollector):
    IMPORTER = generic_exchange_importer.GenericExchangeDataImporter

    async def start(self):
        exchange_manager = await trading_api.create_exchange_builder(self.config, self.exchange_name) \
            .is_simulated() \
            .is_rest_only() \
            .is_without_auth() \
            .is_ignoring_config() \
            .disable_trading_mode() \
            .use_tentacles_setup_config(self.tentacles_setup_config) \
            .build()

        self._load_timeframes_if_necessary()

        # create description
        await self._create_description()

        exchange_id = exchange_manager.id
        await exchange_channel.get_chan(channels_name.OctoBotTradingChannelsName.TICKER_CHANNEL.value,
                                        exchange_id).new_consumer(self.ticker_callback)
        await exchange_channel.get_chan(channels_name.OctoBotTradingChannelsName.RECENT_TRADES_CHANNEL.value,
                                        exchange_id).new_consumer(self.recent_trades_callback)
        await exchange_channel.get_chan(channels_name.OctoBotTradingChannelsName.ORDER_BOOK_CHANNEL.value,
                                        exchange_id).new_consumer(self.order_book_callback)
        await exchange_channel.get_chan(channels_name.OctoBotTradingChannelsName.KLINE_CHANNEL.value,
                                        exchange_id).new_consumer(self.kline_callback)
        await exchange_channel.get_chan(channels_name.OctoBotTradingChannelsName.OHLCV_CHANNEL.value,
                                        exchange_id).new_consumer(self.ohlcv_callback)

        await asyncio.gather(*asyncio.all_tasks(asyncio.get_event_loop()))

    async def ticker_callback(self, exchange: str, exchange_id: str,
                              cryptocurrency: str, symbol: str, ticker):
        self.logger.info(f"TICKER : CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} || TICKER = {ticker}")
        await self.save_ticker(timestamp=time.time(), exchange=exchange,
                               cryptocurrency=cryptocurrency, symbol=symbol, ticker=ticker)

    async def order_book_callback(self, exchange: str, exchange_id: str,
                                  cryptocurrency: str, symbol: str, asks, bids):
        self.logger.info(f"ORDERBOOK : CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} "
                         f"|| ASKS = {asks} || BIDS = {bids}")
        await self.save_order_book(timestamp=time.time(), exchange=exchange,
                                   cryptocurrency=cryptocurrency, symbol=symbol, asks=asks, bids=bids)

    async def recent_trades_callback(self, exchange: str, exchange_id: str,
                                     cryptocurrency: str, symbol: str, recent_trades):
        self.logger.info(f"RECENT TRADE : CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} "
                         f"|| RECENT TRADE = {recent_trades}")
        await self.save_recent_trades(timestamp=time.time(), exchange=exchange,
                                      cryptocurrency=cryptocurrency, symbol=symbol, recent_trades=recent_trades)

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle):
        self.logger.info(f"OHLCV : CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} "
                         f"|| TIME FRAME = {time_frame} || CANDLE = {candle}")
        await self.save_ohlcv(timestamp=time.time(), exchange=exchange,
                              cryptocurrency=cryptocurrency, symbol=symbol, time_frame=time_frame, candle=candle)

    async def kline_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, kline):
        self.logger.info(f"KLINE : CRYPTOCURRENCY = {cryptocurrency} || SYMBOL = {symbol} "
                         f"|| TIME FRAME = {time_frame} || KLINE = {kline}")
        await self.save_kline(timestamp=time.time(), exchange=exchange,
                              cryptocurrency=cryptocurrency, symbol=symbol, time_frame=time_frame, kline=kline)
