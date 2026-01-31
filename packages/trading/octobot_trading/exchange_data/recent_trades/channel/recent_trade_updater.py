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

import octobot_commons.html_util as html_util

import octobot_trading.errors as errors
import octobot_trading.exchange_data.recent_trades.channel.recent_trade as recent_trade_channel
import octobot_trading.constants as constants
import octobot_trading.enums as enums


class RecentTradeUpdater(recent_trade_channel.RecentTradeProducer):
    CHANNEL_NAME = constants.RECENT_TRADES_CHANNEL
    RECENT_TRADE_REFRESH_TIME = 5
    RECENT_TRADE_LIMIT = 20  # should be < to RecentTradesManager's MAX_TRADES_COUNT

    def __init__(self, channel):
        super().__init__(channel)
        self.refresh_time = RecentTradeUpdater.RECENT_TRADE_REFRESH_TIME

    async def init_recent_trades(self):
        pair = None
        try:
            for pair in self._get_pairs_to_update():
                recent_trades = await self.channel.exchange_manager.exchange.\
                    get_recent_trades(pair, limit=self.RECENT_TRADE_LIMIT)
                if recent_trades:
                    await self.push(pair, recent_trades)
            await asyncio.sleep(self.refresh_time)
        except Exception as e:
            self.logger.exception(
                e,
                True,
                f"Fail to initialize {pair} recent trades : {html_util.get_html_summary_if_relevant(e)}"
            )

    async def start(self):
        refresh_threshold = self.channel.exchange_manager.get_rest_pairs_refresh_threshold()
        if refresh_threshold is enums.RestExchangePairsRefreshMaxThresholds.MEDIUM:
            self.refresh_time = 9
        elif refresh_threshold is enums.RestExchangePairsRefreshMaxThresholds.SLOW:
            self.refresh_time = 15
        await self.init_recent_trades()
        # check if channel is not None to avoid attribute error if channel has been concurrently closed
        if self.channel is not None:
            if self.channel.is_paused:
                await self.pause()
            else:
                await self.start_update_loop()

    async def start_update_loop(self):
        while not self.should_stop and not self.channel.is_paused:
            try:
                for pair in self._get_pairs_to_update():
                    recent_trades = await self.channel.exchange_manager.exchange.\
                        get_recent_trades(pair, limit=self.RECENT_TRADE_LIMIT)
                    if recent_trades:
                        try:
                            await self.push(pair, recent_trades)
                        except TypeError:
                            pass
                await asyncio.sleep(self.refresh_time)
            except errors.FailedRequest as err:
                sleep_time = constants.FAILED_NETWORK_REQUEST_RETRY_ATTEMPTS
                self.logger.warning(
                    f"Impossible to fetch recent trades. Retry in {sleep_time} seconds: "
                    f"{html_util.get_html_summary_if_relevant(err)}"
                )
                # avoid spamming on disconnected situation
                await asyncio.sleep(sleep_time)
            except errors.NotSupported:
                self.logger.warning(f"{self.channel.exchange_manager.exchange_name} is not supporting updates")
                await self.pause()
            except Exception as e:
                self.logger.exception(
                    e,
                    True,
                    f"Fail to update recent trades : {html_util.get_html_summary_if_relevant(e)}"
                )

    def _get_pairs_to_update(self):
        return self.channel.exchange_manager.exchange_config.traded_symbol_pairs + self.channel.exchange_manager.exchange_config.additional_traded_pairs

    async def resume(self) -> None:
        await super().resume()
        if not self.is_running:
            await self.run()
