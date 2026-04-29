# pylint: disable=E0611
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
import time

import octobot_commons.html_util as html_util

import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.exchange_data.markets.channel.markets as markets_channel


class MarketsUpdater(markets_channel.MarketsProducer):
    CHANNEL_NAME = constants.MARKETS_CHANNEL
    SPOT_MARKETS_REFRESH_TIME = 86400 # 1 time per day
    FUTURES_MARKETS_REFRESH_TIME = 86400 # 1 time per day
    OPTION_MARKETS_REFRESH_TIME = 600 # every 10 minutes

    def __init__(self, channel):
        super().__init__(channel)
        self.refresh_time = self._get_refresh_time()
        self.tasks = []

    async def start(self):
        self.tasks = [asyncio.create_task(self.market_watcher())]

    def _get_refresh_time(self):
        if self.channel.exchange_manager.is_future:
            return self.FUTURES_MARKETS_REFRESH_TIME
        elif self.channel.exchange_manager.is_option:
            return self.OPTION_MARKETS_REFRESH_TIME
        return self.SPOT_MARKETS_REFRESH_TIME

    async def market_watcher(self):
        """
        Manage markets data refreshing for all symbols
        """
        while not self.should_stop: # As there is not markets channel consumer, we shouldn't check self.channel.is_paused for now
            try:
                started_time = time.time()
                markets = await self.channel.exchange_manager.exchange.refresh_markets()
                await self.push(markets)
                sleep_time = max(self.refresh_time - (time.time() - started_time), 0)
                await asyncio.sleep(sleep_time)
            except errors.FailedRequest as e:
                self.logger.warning(str(e))
                # avoid spamming on disconnected situation
                await asyncio.sleep(constants.FAILED_NETWORK_REQUEST_RETRY_ATTEMPTS)
            except errors.NotSupported:
                self.logger.warning(f"{self.channel.exchange_manager.exchange_name} is not supporting updates")
                await self.pause()
            except Exception as e:
                self.logger.exception(
                    e,
                    True,
                    f"Failed to update markets data : {html_util.get_html_summary_if_relevant(e)}"
                )

    async def resume(self) -> None:
        await super().resume()
        if not self.is_running:
            for task in self.tasks:
                task.cancel()
            await self.run()

    async def stop(self) -> None:
        await super().stop()
        for task in self.tasks:
            task.cancel()
        self.tasks = []
