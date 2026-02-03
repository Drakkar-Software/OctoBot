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

import async_channel.constants as async_channel_constants

import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.enums as enums
import octobot_trading.constants as constants


class TickerProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, symbol, ticker):
        await self.perform(symbol, ticker)
        await self._on_ticker_push(symbol, ticker)

    async def perform(self, symbol, ticker):
        try:
            if self.channel.get_filtered_consumers(symbol=async_channel_constants.CHANNEL_WILDCARD) or \
                    self.channel.get_filtered_consumers(symbol=symbol):  #
                if ticker:  # and price_ticker_is_initialized
                    self.channel.exchange_manager.get_symbol_data(symbol).handle_ticker_update(ticker)
                    await self.send(cryptocurrency=self.channel.exchange_manager.exchange.
                                    get_pair_cryptocurrency(symbol),
                                    symbol=symbol,
                                    ticker=ticker)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, cryptocurrency, symbol, ticker):
        for consumer in self.channel.get_filtered_consumers(symbol=symbol):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "ticker": ticker
            })

    async def _on_ticker_push(self, symbol, ticker):
        await self._push_mini_ticker(symbol, ticker)
        if self.channel.exchange_manager.is_future:
            await self._push_future_data(symbol, ticker)

    async def _push_mini_ticker(self, pair, ticker):
        """
        Mini ticker
        """
        try:
            if not ticker[enums.ExchangeConstantsTickersColumns.CLOSE.value]:
                # no need to push when there is not even a close price (0 or None)
                return
            await exchanges_channel.get_chan(
                constants.MINI_TICKER_CHANNEL,
                self.channel.exchange_manager.id
            ).get_internal_producer().push(
                pair,
                {
                    enums.ExchangeConstantsMiniTickerColumns.HIGH_PRICE.value:
                        ticker[enums.ExchangeConstantsTickersColumns.HIGH.value],
                    enums.ExchangeConstantsMiniTickerColumns.LOW_PRICE.value:
                        ticker[enums.ExchangeConstantsTickersColumns.LOW.value],
                    enums.ExchangeConstantsMiniTickerColumns.OPEN_PRICE.value:
                        ticker[enums.ExchangeConstantsTickersColumns.OPEN.value],
                    enums.ExchangeConstantsMiniTickerColumns.CLOSE_PRICE.value:
                        ticker[enums.ExchangeConstantsTickersColumns.CLOSE.value],
                    enums.ExchangeConstantsMiniTickerColumns.VOLUME.value:
                        ticker[enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value],
                    enums.ExchangeConstantsMiniTickerColumns.TIMESTAMP.value:
                        ticker[enums.ExchangeConstantsTickersColumns.TIMESTAMP.value]
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to parse mini ticker : {e}")

    async def _push_future_data(self, symbol: str, ticker: dict):
        if self.channel.exchange_manager.exchange.MARK_PRICE_IN_TICKER:
            await self._push_mark_price(symbol, ticker)

        if self.channel.exchange_manager.exchange.FUNDING_IN_TICKER:
            await self._push_funding_rate(symbol, ticker)

    async def _push_mark_price(self, symbol: str, ticker: dict):
        try:
            ticker = self.channel.exchange_manager.exchange.parse_mark_price(ticker, from_ticker=True)
            await exchanges_channel.get_chan(constants.MARK_PRICE_CHANNEL,
                                             self.channel.exchange_manager.id).get_internal_producer().push(
                symbol,
                decimal.Decimal(str(ticker[enums.ExchangeConstantsMarkPriceColumns.MARK_PRICE.value])),
                mark_price_source=enums.MarkPriceSources.TICKER_CLOSE_PRICE.value
            )
        except Exception as e:
            self.logger.exception(e, True, f"Fail to update mark price from ticker : {e}")

    async def _push_funding_rate(self, symbol: str, ticker: dict):
        try:
            funding_from_ticker = self.channel.exchange_manager.exchange.parse_funding(ticker, from_ticker=True)
            if not funding_from_ticker:
                # not enough info, don't push possibly false data
                return
            await exchanges_channel.get_chan(constants.FUNDING_CHANNEL, self.channel.exchange_manager.id)\
                .get_internal_producer().push(
                    symbol,
                    funding_from_ticker[enums.ExchangeConstantsFundingColumns.FUNDING_RATE.value],
                    funding_from_ticker[enums.ExchangeConstantsFundingColumns.PREDICTED_FUNDING_RATE.value],
                    funding_from_ticker[enums.ExchangeConstantsFundingColumns.NEXT_FUNDING_TIME.value],
                    funding_from_ticker[enums.ExchangeConstantsFundingColumns.LAST_FUNDING_TIME.value],
            )
        except Exception as e:
            self.logger.exception(e, True, f"Fail to update funding rate from ticker : {e}")


class TickerChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = TickerProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer


class MiniTickerProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, symbol, mini_ticker):
        await self.perform(symbol, mini_ticker)

    async def perform(self, symbol, mini_ticker):
        try:
            if self.channel.get_filtered_consumers(symbol=async_channel_constants.CHANNEL_WILDCARD) or \
                    self.channel.get_filtered_consumers(symbol=symbol):
                if mini_ticker:
                    self.channel.exchange_manager.get_symbol_data(symbol).handle_mini_ticker_update(mini_ticker)
                    await self.send(cryptocurrency=self.channel.exchange_manager.exchange.
                                    get_pair_cryptocurrency(symbol),
                                    symbol=symbol,
                                    mini_ticker=mini_ticker)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, cryptocurrency, symbol, mini_ticker):
        for consumer in self.channel.get_filtered_consumers(symbol=symbol):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "mini_ticker": mini_ticker
            })


class MiniTickerChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = MiniTickerProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer
