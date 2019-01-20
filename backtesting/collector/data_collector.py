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

from tools.logging.logging_util import get_logger

import ccxt.async_support as ccxt

from backtesting.collector.exchange_collector import ExchangeDataCollector
from config import CONFIG_TIME_FRAME, CONFIG_EXCHANGES
from trading.exchanges.exchange_manager import ExchangeManager


class DataCollector:
    def __init__(self, config, auto_start=True):
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

        self.exchange_data_collectors = []
        self.exchange_data_collectors_tasks = []
        self.config[CONFIG_TIME_FRAME] = []

        self.auto_start = auto_start

    async def create_exchange_data_collectors(self):
        available_exchanges = ccxt.exchanges
        for exchange_class_string in self.config[CONFIG_EXCHANGES]:
            if exchange_class_string in available_exchanges:
                exchange_type = getattr(ccxt, exchange_class_string)

                exchange_manager = ExchangeManager(self.config, exchange_type, is_simulated=False, rest_only=True)
                await exchange_manager.initialize()
                exchange_inst = exchange_manager.get_exchange()

                exchange_data_collector = ExchangeDataCollector(self.config, exchange_inst)

                if not exchange_data_collector.get_symbols() or not exchange_data_collector.time_frames:
                    self.logger.warning("{0} exchange not started (not enough symbols or timeframes)"
                                        .format(exchange_class_string))
                else:
                    self.exchange_data_collectors.append(exchange_data_collector)
                    self.exchange_data_collectors_tasks.append(exchange_data_collector.start())
            else:
                self.logger.error(f"{exchange_class_string} exchange not found")

    async def execute_with_specific_target(self, exchange, symbol):
        try:
            exchange_type = getattr(ccxt, exchange)
            exchange_manager = ExchangeManager(self.config, exchange_type, is_simulated=False, rest_only=True,
                                               ignore_config=True)
            await exchange_manager.initialize()
            exchange_inst = exchange_manager.get_exchange()
            exchange_data_collector = ExchangeDataCollector(self.config, exchange_inst, symbol)
            files = await exchange_data_collector.load_available_data()
            return files[0]
        except Exception as e:
            self.logger.exception(e)
            raise e

    def stop(self):
        for data_collector in self.exchange_data_collectors:
            data_collector.stop()

    async def start(self):
        if self.auto_start:
            self.logger.info("Create data collectors...")
            await self.create_exchange_data_collectors()

        await asyncio.gather(*self.exchange_data_collectors_tasks)
