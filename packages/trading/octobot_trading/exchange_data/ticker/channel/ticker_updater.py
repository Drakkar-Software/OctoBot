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
import contextlib

import octobot_commons.html_util as html_util

import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.exchange_data.ticker.channel.ticker as ticker_channel
import octobot_trading.enums as enums
import octobot_trading.exchanges.exchange_websocket_factory as exchange_websocket_factory


class TickerUpdater(ticker_channel.TickerProducer):
    # set True if this channels should be notified when traded symbols are updated
    TO_NOTIFY_ON_TRADED_SYMBOLS_UPDATE: bool = True
    CHANNEL_NAME = constants.TICKER_CHANNEL
    TICKER_REFRESH_TIME = 64
    TICKER_FUTURE_REFRESH_TIME = 14
    TICKER_REFRESH_DELAY_THRESHOLD = 10

    def __init__(self, channel):
        super().__init__(channel)
        self._added_pairs = []
        self.is_fetching_future_data = False
        self.refresh_time = self.TICKER_REFRESH_TIME
        self.updating_pairs = set()

    async def start(self):
        use_futures = self._should_use_future()
        if use_futures:
            self.is_fetching_future_data = True
            self.refresh_time = self.TICKER_FUTURE_REFRESH_TIME
        if self.channel.is_paused:
            await self.pause()
        else:
            if use_futures or self._should_loop():
                # initialize ticker
                await asyncio.gather(*[self._fetch_ticker(pair)
                                       for pair in self._get_pairs_to_update()])
                await asyncio.sleep(self.refresh_time)
                await self.start_update_loop()
            else:
                self.logger.debug(
                    f"Ticker update loop disabled: update is managed by websocket. "
                    f"Updater remains available for forced updates."
                )

    async def start_update_loop(self):
        while not self.should_stop and not self.channel.is_paused:
            try:
                for pair in self._get_pairs_to_update():
                    await self._fetch_ticker(pair)

                await asyncio.sleep(self.refresh_time)
            except errors.NotSupported:
                self.logger.warning(f"{self.channel.exchange_manager.exchange_name} is not supporting updates")
                await self.pause()
            except Exception as e:
                self.logger.exception(
                    e,
                    True,
                    f"Fail to update ticker : {html_util.get_html_summary_if_relevant(e)}"
                )

    async def _fetch_ticker(self, pair):
        try:
            await self.fetch_and_push_pair(pair)
        except errors.FailedRequest as e:
            self.logger.warning(html_util.get_html_summary_if_relevant(e))
            # avoid spamming on disconnected situation
            await asyncio.sleep(constants.FAILED_NETWORK_REQUEST_RETRY_ATTEMPTS)

    async def fetch_and_push_pair(self, pair: str):
        with self._single_pair_update(pair) as can_update:
            if can_update:
                ticker: dict = await self.channel.exchange_manager.exchange.get_price_ticker(pair)
                if self._is_valid(ticker):
                    await self.push(pair, ticker)
                else:
                    self.logger.debug(f"Ignored incomplete ticker: {ticker}")
            else:
                self.logger.debug(f"Skipping {pair} ticker update request: an update is already processing")

    async def trigger_ticker_update(self, symbol: str):
        self.logger.debug(f"Triggered ticker update for {symbol}")
        await self.fetch_and_push_pair(symbol)

    @contextlib.contextmanager
    def _single_pair_update(self, pair: str):
        can_update = False
        try:
            can_update = pair not in self.updating_pairs
            if can_update:
                self.updating_pairs.add(pair)
            yield can_update
        finally:
            if can_update:
                self.updating_pairs.remove(pair)

    @staticmethod
    def _is_valid(ticker):
        try:
            # at least require close, volume and timestamp
            if not (
                ticker.get(enums.ExchangeConstantsTickersColumns.CLOSE.value)
                and ticker.get(enums.ExchangeConstantsTickersColumns.TIMESTAMP.value)
            ):
                return False
            if not (
                ticker.get(enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value)
                or ticker.get(enums.ExchangeConstantsTickersColumns.QUOTE_VOLUME.value)
            ):
                # require either base or quote volume
                return False
            return True
        except KeyError:
            return False

    def _get_pairs_to_update(self):
        return self.channel.exchange_manager.exchange_config.traded_symbol_pairs + self._added_pairs


    def _should_loop(self):
        """
        Loop when websocket ticker channel not available
        """
        return not exchange_websocket_factory.is_channel_managed_by_websocket(
            self.channel.exchange_manager, constants.TICKER_CHANNEL
        )

    """
    Future data management
    """

    def _should_use_future(self):
        return (
            self.channel.exchange_manager.is_future and (
                self.channel.exchange_manager.exchange.FUNDING_IN_TICKER
                or self.channel.exchange_manager.exchange.MARK_PRICE_IN_TICKER
            )
        )

    async def modify(self, added_pairs=None, removed_pairs=None):
        if added_pairs:
            to_add_pairs = [pair
                            for pair in added_pairs
                            if pair not in self._get_pairs_to_update()]
            if to_add_pairs:
                self._added_pairs += to_add_pairs
                self.logger.info(f"Added pairs : {to_add_pairs}")
                for pair in to_add_pairs:
                    # ensure pair symbol data and ticker are initialized
                    await self.trigger_ticker_update(pair)
                self._update_refresh_time()

        if removed_pairs:
            self._added_pairs = [pair for pair in self._added_pairs if pair not in removed_pairs]
            self.logger.info(f"Removed pairs : {removed_pairs}")
            self._update_refresh_time()

    def _update_refresh_time(self):
        if self.is_fetching_future_data:
            # do not change ticker update rate on futures
            return
        pairs_to_update_count = len(self._get_pairs_to_update())
        delay_multiplier = pairs_to_update_count // self.TICKER_REFRESH_DELAY_THRESHOLD + 1
        # there can be many ticker requests when a large number of currency is in a
        # portfolio, in this case, limit those requests
        self.refresh_time = self.TICKER_REFRESH_TIME * delay_multiplier

    async def resume(self) -> None:
        await super().resume()
        if not self.is_running:
            await self.run()
