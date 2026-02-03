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
import decimal

import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging

import octobot_trading.enums as enums
import octobot_trading.util as util
import octobot_trading.constants as constants
import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.exchanges


class PricesManager(util.Initializable):
    MARK_PRICE_FETCH_TIMEOUT = 5 * commons_constants.MINUTE_TO_SECONDS

    def __init__(self, exchange_manager, symbol: str):
        super().__init__()
        self.mark_price: decimal.Decimal = constants.ZERO
        self.mark_price_set_time: float = 0
        self.mark_price_from_sources: dict[str, tuple[decimal.Decimal, float]] = {}
        self.exchange_manager: octobot_trading.exchanges.ExchangeManager = exchange_manager
        self.symbol: str = symbol
        self.logger: logging.BotLogger = logging.get_logger(f"{self.__class__.__name__}[{self.exchange_manager.exchange_name}]")
        self.price_validity: float = self._compute_mark_price_validity_timeout()

        # warning: should only be created in the async loop thread
        self.valid_price_received_event: asyncio.Event = asyncio.Event()

    async def initialize_impl(self):
        """
        Initialize PricesManager attributes with default
        """
        self._reset_prices()

    def initialized(self):
        return self.mark_price is not constants.ZERO

    def stop(self):
        self._reset_prices()
        self.exchange_manager = None # type: ignore

    def set_mark_price(self, mark_price, mark_price_source) -> bool:
        """
        Set the mark price if the mark price come from MarkPriceSources.EXCHANGE_MARK_PRICE
        Set the mark price if the mark price come from MarkPriceSources.RECENT_TRADE_AVERAGE and
        if it's not the first update for MarkPriceSources.RECENT_TRADE_AVERAGE
        Set the mark price if the mark price come from MarkPriceSources.TICKER_CLOSE_PRICE and
        if other sources have expired
        :param mark_price: the mark price value from mark_price_source in float
        :param mark_price_source: the mark_price source (from MarkPriceSources)
        :return True if mark price got updated
        """
        is_mark_price_updated = False
        if mark_price_source == enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value:
            self._set_mark_price_value(mark_price)
            is_mark_price_updated = True

        # set mark price value if MarkPriceSources.RECENT_TRADE_AVERAGE.value has already been updated
        elif mark_price_source == enums.MarkPriceSources.RECENT_TRADE_AVERAGE.value:
            if self.mark_price_from_sources.get(enums.MarkPriceSources.RECENT_TRADE_AVERAGE.value, None) is not None:
                self._set_mark_price_value(mark_price)
                is_mark_price_updated = True
            else:
                # set time at 0 to ensure invalid price but keep track of initialization
                self.mark_price_from_sources[mark_price_source] = (mark_price, 0)

        # set mark price value if other sources have expired
        elif mark_price_source in (enums.MarkPriceSources.TICKER_CLOSE_PRICE.value,
                                   enums.MarkPriceSources.CANDLE_CLOSE_PRICE.value) and not \
                self._are_other_sources_valid(mark_price_source):
            self._set_mark_price_value(mark_price)
            is_mark_price_updated = True

        if is_mark_price_updated:
            self.mark_price_from_sources[mark_price_source] = \
                (mark_price, self.exchange_manager.exchange.get_exchange_current_time())
        return is_mark_price_updated

    def get_mark_price_no_wait(self) -> decimal.Decimal:
        self._ensure_price_validity()
        if not self.valid_price_received_event.is_set():
            raise ValueError(f"No up to date mark price for {self.exchange_manager.exchange_name}")
        return self.mark_price

    async def get_mark_price(self, timeout=MARK_PRICE_FETCH_TIMEOUT) -> decimal.Decimal:
        """
        Return mark price if valid
        :param timeout: event wait timeout
        :return: the mark price if valid
        """
        self._ensure_price_validity()
        if not self.valid_price_received_event.is_set():
            try:
                self.exchange_manager.ensure_reachability()
                if self.exchange_manager.is_backtesting:
                    if self.exchange_manager.exchange.is_skipping_empty_candles_in_ohlcv_fetch():
                        # missing candles can happen if no traded took place in their time frame. Don't raise and use
                        # last set price
                        return self.mark_price
                    # should never happen in backtesting: mark price is either available
                    # or exchange should be unreachable
                    raise asyncio.TimeoutError()
                else:
                    self.logger.debug(
                        f"Asking for {self.exchange_manager.exchange_name} {self.symbol} mark price update"
                    )
                    await self._trigger_mark_price_update()

                await asyncio.wait_for(self.valid_price_received_event.wait(), timeout)
                self.logger.debug(
                    f"{self.exchange_manager.exchange_name} {self.symbol} mark price update received: {self.mark_price}"
                )
            except asyncio.TimeoutError:
                self.logger.warning("Timeout when waiting for current market price. This probably means that the "
                                    "required mark price market as a very low liquidity. Market price will be "
                                    "available as soon as a trade will happen on this market.")
                raise
        return self.mark_price

    async def _trigger_mark_price_update(self):
        # trigger a mark price refresh from a ticker update
        try:
            await exchange_channel.get_chan(
                constants.TICKER_CHANNEL,
                self.exchange_manager.id
            ).get_producers()[0].trigger_ticker_update(self.symbol)
        except IndexError as err:
            # missing producer
            self.logger.exception(
                err,
                True,
                f"Missing {constants.TICKER_CHANNEL} channel producer. Can't force mark price update from this channel"
            )
        except Exception as err:
            self.logger.exception(err, True, f"Unexpected error when triggering ticker update: {err}")

    def _set_mark_price_value(self, mark_price):
        """
        Called when a new mark price value has been calculated or provided by the exchange
        """
        self.mark_price = mark_price
        self.mark_price_set_time = self.exchange_manager.exchange.get_exchange_current_time()
        self.valid_price_received_event.set()

    def _are_other_sources_valid(self, mark_price_source):
        """
        Check if other sources a out of validity
        """
        for source in enums.MarkPriceSources:
            source_mark_price = self.mark_price_from_sources.get(source.value, None)
            if source_mark_price is not None and \
                    mark_price_source != source.value and \
                    self._is_mark_price_valid(source_mark_price[1]):
                return True
        return False

    def _ensure_price_validity(self):
        """
        Clear the event price validity event if the mark price has expired
        """
        if not self._is_mark_price_valid(self.mark_price_set_time):
            self.valid_price_received_event.clear()

    def _compute_mark_price_validity_timeout(self) -> float:
        refresh_threshold = self.exchange_manager.get_rest_pairs_refresh_threshold()
        if refresh_threshold is enums.RestExchangePairsRefreshMaxThresholds.FAST:
            return 3 * commons_constants.MINUTE_TO_SECONDS
        if refresh_threshold is enums.RestExchangePairsRefreshMaxThresholds.MEDIUM:
            return 5 * commons_constants.MINUTE_TO_SECONDS
        return 7 * commons_constants.MINUTE_TO_SECONDS

    def _is_mark_price_valid(self, mark_price_updated_time):
        """
        Check if a mark price value has expired
        :param mark_price_updated_time: the mark price updated time
        :return: True if the difference between mark_price_updated_time and now is < self.price_validity
        """
        return self.exchange_manager.exchange.get_exchange_current_time() - mark_price_updated_time < \
            self.price_validity

    def _reset_prices(self):
        """
        Reset PricesManager attributes values
        """
        self.mark_price = constants.ZERO
        self.mark_price_set_time = 0
        self.valid_price_received_event.clear()
        self.mark_price_from_sources = {}


def calculate_mark_price_from_recent_trade_prices(recent_trade_prices):
    return decimal.Decimal(sum(recent_trade_prices)) / decimal.Decimal(len(recent_trade_prices)) \
        if recent_trade_prices else constants.ZERO
