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
import typing

import octobot_commons.async_job as async_job
import octobot_commons.constants as common_constants
import octobot_commons.html_util as html_util

import octobot_trading.exchange_data.funding.channel.funding as funding_channel
import octobot_trading.exchanges.exchange_websocket_factory as exchange_websocket_factory
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.errors as errors


class FundingUpdater(funding_channel.FundingProducer):
    # set True if this channels should be notified when traded symbols are updated
    TO_NOTIFY_ON_TRADED_SYMBOLS_UPDATE: bool = True
    """
    The Funding Update fetch the exchange funding rate and send it to the Funding Channel
    """

    """
    The updater related channel name
    """
    CHANNEL_NAME = constants.FUNDING_CHANNEL

    """
    The default funding update refresh times in seconds
    """
    FUNDING_REFRESH_TIME = 2 * common_constants.HOURS_TO_SECONDS
    FUNDING_REFRESH_TIME_MIN = 0.2 * common_constants.HOURS_TO_SECONDS
    FUNDING_REFRESH_TIME_MAX = 8 * common_constants.HOURS_TO_SECONDS

    def __init__(self, channel):
        super().__init__(channel)
        # create async jobs
        self.fetch_funding_job = async_job.AsyncJob(self._funding_fetch_and_push,
                                                    execution_interval_delay=self.FUNDING_REFRESH_TIME,
                                                    min_execution_delay=self.FUNDING_REFRESH_TIME_MIN)

    async def initialize(self) -> None:
        """
        Initialize data before starting fetch_funding_job
        """
        next_funding_times = await self._funding_fetch_and_push()
        if next_funding_times \
                and not all(next_funding_time > self.FUNDING_REFRESH_TIME for next_funding_time in next_funding_times):
            min_next_funding_time = min(next_funding_times)
            await asyncio.sleep(self._get_time_until_next_funding(min_next_funding_time))
            # call initialize until a next_funding_time < self.FUNDING_REFRESH_TIME before starting fetch_funding_job
            await self.initialize()

    async def start(self) -> None:
        """
        Start updater jobs
        """
        if not self._should_run():
            self.logger.debug("Ignoring updater start as funding can be found in different sources")
            return

        await self.initialize()
        await self.fetch_funding_job.run()

    async def _funding_fetch_and_push(self) -> list:
        next_funding_times = []
        for pair in self._get_pairs_to_update():
            next_funding_time_candidate = await self.fetch_symbol_funding_rate(pair)
            if next_funding_time_candidate is not None:
                next_funding_times.append(next_funding_time_candidate)
        return next_funding_times

    async def fetch_symbol_funding_rate(self, symbol: str) -> typing.Optional[int]:
        """
        Fetch funding rate from exchange
        :param symbol: the funding symbol to fetch
        :return: the next funding time
        """
        try:
            funding: dict = await self.channel.exchange_manager.exchange.get_funding_rate(symbol)

            if funding:
                next_funding_time = funding[enums.ExchangeConstantsFundingColumns.NEXT_FUNDING_TIME.value]
                await self._push_funding(
                    symbol,
                    funding[enums.ExchangeConstantsFundingColumns.FUNDING_RATE.value],
                    predicted_funding_rate=funding[enums.ExchangeConstantsFundingColumns.PREDICTED_FUNDING_RATE.value],
                    next_funding_time=next_funding_time,
                    last_funding_time=funding[enums.ExchangeConstantsFundingColumns.LAST_FUNDING_TIME.value]
                )
                return next_funding_time
        except errors.NotSupported:
            self.logger.warning(f"{self.channel.exchange_manager.exchange_name} is not supporting funding rate updates")
            await self.pause() 
        except NotImplementedError as ne:
            self.logger.exception(ne, True, f"get_funding_rate is not supported by "
                                            f"{self.channel.exchange_manager.exchange.name} : {ne}")
        except Exception as e:
            self.logger.exception(
                e,
                True,
                f"Fail to update funding rate on {self.channel.exchange_manager.exchange.name} for {symbol} : "
                f"{html_util.get_html_summary_if_relevant(e)}"
            )
        return None

    async def _push_funding(self, symbol, funding_rate, predicted_funding_rate=None,
                            next_funding_time=None, last_funding_time=None) -> None:
        """
        Push funding data to channel
        :param symbol: the funding symbol
        :param funding_rate: the funding rate
        :param predicted_funding_rate: the next predicted funding rate
        :param next_funding_time: the next funding time
        :param last_funding_time: the last funding time
        """
        if predicted_funding_rate is None:
            predicted_funding_rate = constants.ZERO
        if last_funding_time is None:
            last_funding_time = self.channel.exchange_manager.exchange.get_exchange_current_time()
        if next_funding_time is None:
            next_funding_time = last_funding_time + self.FUNDING_REFRESH_TIME_MAX
        await self.push(
            symbol,
            funding_rate,
            predicted_funding_rate,
            next_funding_time,
            last_funding_time,
        )

    def _should_run(self):
        """
        Check if the funding update should run
        :return: the check result
        """
        if not self.channel.exchange_manager.is_future:
            return False
        # if this is run, it means the funding channel is not directly updated by websockets
        # therefore, it should run if:
        # - ticker updater is on (ticker not managed by ws) and FUNDING_IN_TICKER is False
        # - or ticker updater is off (ticker managed by ws) (as we are here, it means funding is not handled by ws)
        is_ticker_updater_on = not exchange_websocket_factory.is_channel_managed_by_websocket(
            self.channel.exchange_manager, constants.TICKER_CHANNEL
        )
        return (
            (
                is_ticker_updater_on and not self.channel.exchange_manager.exchange.FUNDING_IN_TICKER
            )
            or not is_ticker_updater_on
        )

    def _get_time_until_next_funding(self, next_funding_time):
        """
        Calculates the time between now and the next funding time (should not be > FUNDING_REFRESH_TIME_MAX)
        :param next_funding_time: the next funding time
        :return:
        """
        should_sleep_time = next_funding_time - self.channel.exchange_manager.exchange.get_exchange_current_time()
        return (
            should_sleep_time
            if should_sleep_time < self.FUNDING_REFRESH_TIME_MAX
            else self.FUNDING_REFRESH_TIME
        )

    async def modify(self, added_pairs=None, removed_pairs=None):
        if not self._should_run():
            return
        if added_pairs:
            await self._funding_fetch_and_push()

    def _get_pairs_to_update(self):
        return self.channel.exchange_manager.exchange_config.traded_symbol_pairs + self.channel.exchange_manager.exchange_config.additional_traded_pairs

    async def stop(self) -> None:
        """
        Stop producer by stopping fetch_funding_job
        """
        await super().stop()
        if not self._should_run():
            return
        self.fetch_funding_job.stop()

    async def resume(self) -> None:
        """
        Resume producer by restarting fetch_funding_job
        """
        await super().resume()
        if not self._should_run():
            return
        if not self.is_running:
            await self.run()
