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
import time
from asyncio import CancelledError
from typing import Dict

from backtesting import backtesting_enabled, BacktestingEndedException
from config import TimeFramesMinutes, MINUTE_TO_SECONDS, UPDATER_MAX_SLEEPING_TIME
from core.consumers_producers.producers import ExchangeProducer


class OHLCVUpdaterProducer(ExchangeProducer):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.refreshed_times: int = 0
        self.last_update: int = 0

    async def send(self, data):
        self.refreshed_times += 1
        self.last_update = time.time()
        await super().send(data)


class OHLCVUpdater(ExchangeProducer):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.config = self.exchange.config
        self.updated_time_frames = self.exchange.time_frames
        self.updated_traded_pairs = self.exchange.traded_pairs

        self.ohlcv_producers: Dict[Dict[OHLCVUpdaterProducer]] = {}
        self.symbol_evaluators = []

        self.backtesting_enabled = backtesting_enabled(self.config)

    # should be called to force refresh
    async def receive(self):
        await self.perform()

    async def start(self):
        # create producers
        self.ohlcv_producers = {
            symbol: {
                time_frame: OHLCVUpdaterProducer(self.exchange)
                for time_frame in self.updated_time_frames
            }
            for symbol in self.updated_traded_pairs
        }

        self.symbol_evaluators = [
            self.exchange.get_symbol_data(symbol)
            for symbol in self.updated_traded_pairs
        ]

        while self.should_stop:
            try:
                await self.perform()
            except CancelledError:
                self.logger.info("Update tasks cancelled.")
            except Exception as e:
                self.logger.error(f"exception when triggering update: {e}")
                self.logger.exception(e)

    async def perform(self):
        now = time.time()
        update_tasks = []

        for symbol in self.updated_traded_pairs:
            for time_frame in self.updated_time_frames:
                producer: OHLCVUpdaterProducer = self.ohlcv_producers[symbol][time_frame]

                # backtesting doesn't need to wait a specific time frame to end to refresh data
                if self.backtesting_enabled:
                    update_tasks.append(self._refresh_backtesting_time_frame_data(time_frame, symbol, producer))

                # if data from this time frame needs an update
                elif now - producer.last_update >= TimeFramesMinutes[time_frame] * MINUTE_TO_SECONDS:
                    update_tasks.append(self._refresh_time_frame_data(time_frame, symbol, producer))

        await asyncio.gather(*update_tasks)

        self.logger.info("Refreshed")

        # if update_tasks:
        #     await self.trigger_symbols_finalize()
        # TODO will occurs in the futur evaluator_task_manager

        if self.backtesting_enabled:
            await self.update_backtesting_order_status()

        if self.should_stop:
            await self._update_pause(now)

    # calculate task sleep time between each refresh
    async def _update_pause(self, now):
        sleeping_time = 0
        if not self.backtesting_enabled:
            sleeping_time = UPDATER_MAX_SLEEPING_TIME - (time.time() - now)
        if sleeping_time > 0:
            await asyncio.sleep(sleeping_time)

    async def force_refresh_data(self, time_frame, symbol):
        if not self.backtesting_enabled:
            await self._refresh_time_frame_data(time_frame, symbol, self.ohlcv_producers[symbol][time_frame])

    # backtesting
    def _init_backtesting_if_necessary(self, time_frames):
        # test if we need to initialize backtesting features
        if self.backtesting_enabled:
            for symbol in self.updated_traded_pairs:
                self.exchange.get_exchange().init_candles_offset(time_frames, symbol)

    async def _refresh_backtesting_time_frame_data(self, time_frame, symbol, producer: OHLCVUpdaterProducer):
        try:
            if self.exchange.get_exchange().should_update_data(time_frame, symbol):
                await producer.send(True)  # TODO
        except BacktestingEndedException as e:
            self.logger.info(e)
            self.keep_running = False
            await self.exchange.get_exchange().end_backtesting(symbol)

    # currently used only during backtesting, will force refresh of each supervised task
    async def update_backtesting_order_status(self):
        order_manager = self.exchange.get_trader().get_order_manager()
        await order_manager.force_update_order_status(simulated_time=True)

    async def _refresh_time_frame_data(self, time_frame, symbol, producer: OHLCVUpdaterProducer):
        try:
            # ask exchange to refresh data
            await self.exchange.get_exchange().get_symbol_prices(symbol, time_frame)
            await producer.send(True)  # TODO
        except CancelledError as e:
            raise e
        except Exception as e:
            self.logger.error(f" Error when refreshing data for time frame {time_frame}: {e}")
            self.logger.exception(e)

    async def trigger_symbols_finalize(self):
        sort_symbol_evaluators = sorted(self.symbol_evaluators,
                                        key=lambda s: abs(s.get_average_strategy_eval(self.exchange)),
                                        reverse=True)
        for symbol_evaluator in sort_symbol_evaluators:
            await symbol_evaluator.finalize(self.exchange)

    def get_refreshed_times(self, time_frame, symbol) -> int:
        try:
            return self.ohlcv_producers[symbol][time_frame].refreshed_times
        except KeyError:
            return 0
