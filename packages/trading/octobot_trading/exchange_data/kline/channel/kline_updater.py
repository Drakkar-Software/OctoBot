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
import octobot_trading.exchange_data.kline.channel.kline as kline_channel
import octobot_trading.enums as enums


class KlineUpdater(kline_channel.KlineProducer):
    # set True if this channels should be notified when traded symbols are updated
    TO_NOTIFY_ON_TRADED_SYMBOLS_UPDATE: bool = True
    CHANNEL_NAME = constants.KLINE_CHANNEL
    KLINE_REFRESH_TIME = 8
    QUICK_KLINE_REFRESH_TIME = 3

    def __init__(self, channel):
        super().__init__(channel)
        self.refresh_time = KlineUpdater.KLINE_REFRESH_TIME
        self.tasks = []

    async def start(self):
        """
        Creates OHLCV refresh tasks
        """
        refresh_threshold = self.channel.exchange_manager.get_rest_pairs_refresh_threshold()
        if refresh_threshold is enums.RestExchangePairsRefreshMaxThresholds.MEDIUM:
            self.refresh_time = 14
        elif refresh_threshold is enums.RestExchangePairsRefreshMaxThresholds.SLOW:
            self.refresh_time = 22
        if self.channel.is_paused:
            await self.pause()
        else:
            self.tasks = [
                asyncio.create_task(self.time_frame_watcher(time_frame))
                for time_frame in self.channel.exchange_manager.exchange_config.available_time_frames
            ]

    async def time_frame_watcher(self, time_frame):
        """
        Manage timeframe OHLCV data refreshing for all pairs
        """
        while not self.should_stop and not self.channel.is_paused:
            try:
                started_time = time.time()
                quick_sleep = False
                for pair in self._get_pairs_to_update():
                    candle: list = await self.channel.exchange_manager.exchange.get_kline_price(pair, time_frame)
                    try:
                        candle = candle[0]
                        await self.push(time_frame, pair, candle)
                    except TypeError:
                        pass
                    except IndexError:
                        quick_sleep = True
                        self.logger.debug(f"Not enough data to compute kline data in {time_frame} for {pair}. "
                                          f"Kline will be updated with the next refresh.")

                sleep_time = max((self.QUICK_KLINE_REFRESH_TIME if quick_sleep else self.refresh_time)
                                 - (time.time() - started_time), 0)
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
                    f"Failed to update kline data in {time_frame} : {html_util.get_html_summary_if_relevant(e)}"
                )

    def _get_pairs_to_update(self):
        return self.channel.exchange_manager.exchange_config.traded_symbol_pairs + self.channel.exchange_manager.exchange_config.additional_traded_pairs

    async def resume(self) -> None:
        await super().resume()
        if not self.is_running:
            for task in self.tasks:
                task.cancel()
            await self.run()
