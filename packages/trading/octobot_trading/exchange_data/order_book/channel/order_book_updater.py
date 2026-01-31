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
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.constants as constants
import octobot_trading.exchange_data.order_book.channel.order_book as order_book_channel
import octobot_trading.enums as enums


class OrderBookUpdater(order_book_channel.OrderBookProducer):
    CHANNEL_NAME = constants.ORDER_BOOK_CHANNEL
    ORDER_BOOK_REFRESH_TIME = 5

    def __init__(self, channel):
        super().__init__(channel)
        self.refresh_time = OrderBookUpdater.ORDER_BOOK_REFRESH_TIME

    async def start(self):
        refresh_threshold = self.channel.exchange_manager.get_rest_pairs_refresh_threshold()
        if refresh_threshold is enums.RestExchangePairsRefreshMaxThresholds.MEDIUM:
            self.refresh_time = 9
        elif refresh_threshold is enums.RestExchangePairsRefreshMaxThresholds.SLOW:
            self.refresh_time = 15
        if self.channel.is_paused:
            await self.pause()
        else:
            await self.start_update_loop()

    async def start_update_loop(self):
        while not self.should_stop and not self.channel.is_paused:
            try:
                for pair in self._get_pairs_to_update():
                    order_book = await self.channel.exchange_manager.exchange.get_order_book(pair)
                    try:
                        asks, bids = order_book[enums.ExchangeConstantsOrderBookInfoColumns.ASKS.value], \
                                     order_book[enums.ExchangeConstantsOrderBookInfoColumns.BIDS.value]

                        await self.parse_order_book_ticker(pair, asks, bids)
                        await self.push(pair, asks, bids)
                    except errors.FailedRequest as e:
                        self.logger.warning(str(e))
                    except TypeError as e:
                        self.logger.error(f"Failed to fetch order book for {pair} : {e}")
                await asyncio.sleep(self.refresh_time)
            except errors.FailedRequest as e:
                self.logger.warning(str(e))
                # avoid spamming on disconnected situation
                await asyncio.sleep(constants.DEFAULT_FAILED_REQUEST_RETRY_TIME)
            except errors.NotSupported:
                self.logger.warning(f"{self.channel.exchange_manager.exchange_name} is not supporting updates")
                await self.pause()
            except Exception as e:
                self.logger.exception(
                    e, True, f"Fail to update order book : {html_util.get_html_summary_if_relevant(e)}"
                )

    async def parse_order_book_ticker(self, pair, asks, bids):
        """
        Order book ticker
        """
        try:
            if asks and bids:
                await exchanges_channel.get_chan(constants.ORDER_BOOK_TICKER_CHANNEL,
                                                 self.channel.exchange_manager.id).get_internal_producer(). \
                    push(pair,
                         asks[0][1], asks[0][0],
                         bids[0][1], bids[0][0])
        except Exception as e:
            self.logger.error(f"Failed to parse order book ticker : {e}")

    def _get_pairs_to_update(self):
        return self.channel.exchange_manager.exchange_config.traded_symbol_pairs + self.channel.exchange_manager.exchange_config.additional_traded_pairs

    async def resume(self) -> None:
        await super().resume()
        if not self.is_running:
            await self.run()
