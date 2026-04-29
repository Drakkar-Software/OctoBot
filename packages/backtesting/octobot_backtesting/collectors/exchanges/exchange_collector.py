#  Drakkar-Software OctoBot-Backtesting
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
import json
import logging
import abc 

import time

import octobot_commons.constants as commons_constants
import octobot_backtesting.collectors.data_collector as data_collector
import octobot_backtesting.constants as constants
import octobot_backtesting.enums as enums
import octobot_backtesting.importers as importers

try:
    import octobot_trading.constants as trading_constants
except ImportError:
    logging.error("ExchangeDataCollector requires OctoBot-Trading package installed")


class ExchangeDataCollector(data_collector.DataCollector):
    VERSION = "1.1"
    IMPORTER = importers.ExchangeDataImporter

    def __init__(self, config, exchange_name, exchange_type,
                 tentacles_setup_config, symbols, time_frames, use_all_available_timeframes=False,
                 data_format=enums.DataFormats.REGULAR_COLLECTOR_DATA, start_timestamp=None, end_timestamp=None):
        super().__init__(config, data_format=data_format)
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.tentacles_setup_config = tentacles_setup_config
        self.symbols = symbols if symbols else []
        self.time_frames = time_frames if time_frames else []
        self.use_all_available_timeframes = use_all_available_timeframes
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.current_step_index = 0
        self.total_steps = 0
        self.current_step_percent = 0
        self.exchange_id = None
        self.set_file_path()

    def register_exchange_id(self, exchange_id):
        self.exchange_id = exchange_id

    def get_current_step_index(self):
        return self.current_step_index

    def get_total_steps(self):
        return self.total_steps

    def get_current_step_percent(self):
        return self.current_step_percent

    @abc.abstractmethod
    def _load_all_available_timeframes(self):
        raise NotImplementedError("_load_all_available_timeframes is not implemented")

    async def initialize(self):
        self.create_database()
        await self.database.initialize()

        # set config from params
        self.config[commons_constants.CONFIG_TIME_FRAME] = self.time_frames
        # get exchange credentials if available
        existing_exchange_config = self.config.get(commons_constants.CONFIG_EXCHANGES, {}).get(self.exchange_name, {})
        self.config[commons_constants.CONFIG_EXCHANGES] = {self.exchange_name: existing_exchange_config}
        self.config[commons_constants.CONFIG_CRYPTO_CURRENCIES] = {"Symbols": {
            commons_constants.CONFIG_CRYPTO_PAIRS: [str(symbol) for symbol in self.symbols]}}

    def _load_timeframes_if_necessary(self):
        if self.use_all_available_timeframes:
            self._load_all_available_timeframes()
        self.config[commons_constants.CONFIG_TIME_FRAME] = self.time_frames

    async def _create_description(self):
        await self.database.insert(enums.DataTables.DESCRIPTION,
                                   timestamp=time.time(),
                                   version=constants.CURRENT_VERSION,
                                   type=enums.DataType.EXCHANGE.value,
                                   exchange=self.exchange_name,
                                   symbols=json.dumps([symbol.symbol_str for symbol in self.symbols]),
                                   time_frames=json.dumps([tf.value for tf in self.time_frames]),
                                   start_timestamp=int(self.start_timestamp/1000) if self.start_timestamp else 0,
                                   end_timestamp=int(self.end_timestamp/1000) if self.end_timestamp
                                   else int(time.time()) if self.start_timestamp else 0)

    async def save_ticker(self, timestamp, exchange, cryptocurrency, symbol, ticker, multiple=False):
        if not multiple:
            await self.database.insert(enums.ExchangeDataTables.TICKER, timestamp,
                                       exchange_name=exchange, cryptocurrency=cryptocurrency,
                                       symbol=symbol, recent_trades=json.dumps(ticker))
        else:
            await self.database.insert_all(enums.ExchangeDataTables.TICKER, timestamp,
                                           exchange_name=exchange, cryptocurrency=cryptocurrency,
                                           symbol=symbol, recent_trades=[json.dumps(t) for t in ticker])

    async def save_order_book(self, timestamp, exchange, cryptocurrency, symbol, asks, bids, multiple=False):
        if not multiple:
            await self.database.insert(enums.ExchangeDataTables.ORDER_BOOK, timestamp,
                                       exchange_name=exchange, cryptocurrency=cryptocurrency, symbol=symbol,
                                       asks=json.dumps(asks), bids=json.dumps(bids))
        else:
            await self.database.insert_all(enums.ExchangeDataTables.ORDER_BOOK, timestamp,
                                           exchange_name=exchange, cryptocurrency=cryptocurrency, symbol=symbol,
                                           asks=[json.dumps(a) for a in asks],
                                           bids=[json.dumps(b) for b in bids])

    async def save_recent_trades(self, timestamp, exchange, cryptocurrency, symbol, recent_trades, multiple=False):
        if not multiple:
            await self.database.insert(enums.ExchangeDataTables.RECENT_TRADES, timestamp,
                                       exchange_name=exchange, cryptocurrency=cryptocurrency,
                                       symbol=symbol, recent_trades=json.dumps(recent_trades))
        else:
            await self.database.insert_all(enums.ExchangeDataTables.RECENT_TRADES, timestamp,
                                           exchange_name=exchange, cryptocurrency=cryptocurrency,
                                           symbol=symbol, recent_trades=[json.dumps(rt) for rt in recent_trades])

    async def save_ohlcv(self, timestamp, exchange, cryptocurrency, symbol, time_frame, candle, multiple=False):
        if not multiple:
            await self.database.insert(enums.ExchangeDataTables.OHLCV, timestamp,
                                       exchange_name=exchange, cryptocurrency=cryptocurrency,
                                       symbol=symbol, time_frame=time_frame.value,
                                       candle=json.dumps(candle))
        else:
            await self.database.insert_all(enums.ExchangeDataTables.OHLCV, timestamp=timestamp,
                                           exchange_name=exchange, cryptocurrency=cryptocurrency,
                                           symbol=symbol, time_frame=time_frame.value,
                                           candle=[json.dumps(c) for c in candle])

    async def save_kline(self, timestamp, exchange, cryptocurrency, symbol, time_frame, kline, multiple=False):
        if not multiple:
            await self.database.insert(enums.ExchangeDataTables.KLINE, timestamp,
                                       exchange_name=exchange, cryptocurrency=cryptocurrency,
                                       symbol=symbol, time_frame=time_frame.value,
                                       candle=json.dumps(kline))
        else:
            await self.database.insert_all(enums.ExchangeDataTables.KLINE, timestamp=timestamp,
                                           exchange_name=exchange, cryptocurrency=cryptocurrency,
                                           symbol=symbol, time_frame=time_frame.value,
                                           candle=[json.dumps(kl) for kl in kline])

    async def delete_all(self, table, exchange, cryptocurrency, symbol, time_frame=None):
        kwargs = {
            "exchange_name": exchange,
            "cryptocurrency": cryptocurrency,
            "symbol": symbol,
        }
        if time_frame:
            kwargs["time_frame"] = time_frame.value
        await self.database.delete(table, **kwargs)
