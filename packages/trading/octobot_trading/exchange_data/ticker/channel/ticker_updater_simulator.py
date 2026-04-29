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
import octobot_backtesting.api as api
import octobot_backtesting.enums as backtesting_enums

import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_commons.errors as errors

import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.util as util
import octobot_trading.exchange_data.ticker.channel.ticker_updater as ticker_updater


class TickerUpdaterSimulator(ticker_updater.TickerUpdater):
    def __init__(self, channel, importer):
        super().__init__(channel)
        self.exchange_data_importer = importer
        self.exchange_name = self.channel.exchange_manager.exchange_name

        self.last_timestamp_pushed = 0
        self.last_timestamp_pushed_by_symbol = {}
        self.time_consumer = None
        # Only generate tickers from the shortest handled time frame
        shortest_time_frame = self.channel.exchange_manager.exchange_config.get_shortest_time_frame()
        self.ticker_time_frame = shortest_time_frame.value
        self.ticker_time_frame_seconds = common_enums.TimeFramesMinutes[shortest_time_frame] * \
            common_constants.MINUTE_TO_SECONDS

    async def start(self):
        await self.resume()

    async def handle_timestamp(self, timestamp, **kwargs):
        try:
            for pair in self.channel.exchange_manager.exchange_config.traded_symbol_pairs:
                ticker_data = (await self.exchange_data_importer.get_ticker_from_timestamps(
                    exchange_name=self.exchange_name,
                    symbol=pair,
                    inferior_timestamp=timestamp,
                    limit=1))[0]
                if ticker_data[0] > self.last_timestamp_pushed:
                    self.last_timestamp_pushed = ticker_data[0]
                    await self.push(pair, ticker_data[-1])
        except errors.DatabaseNotFoundError as e:
            self.logger.warning(f"Not enough data : {e}")
            await self.pause()
            await self.stop()
        except IndexError as e:
            self.logger.warning(f"Failed to access ticker_data : {e}")

    async def _ticker_from_ohlcv_callback(self, exchange: str, exchange_id: str,
                                          cryptocurrency: str, symbol: str, time_frame, candle):
        if self.ticker_time_frame == time_frame and candle:
            last_candle_timestamp = candle[common_enums.PriceIndexes.IND_PRICE_TIME.value]
            ticker_timestamp = last_candle_timestamp + self.ticker_time_frame_seconds
            if ticker_timestamp > self.last_timestamp_pushed_by_symbol[symbol]:
                self.last_timestamp_pushed_by_symbol[symbol] = ticker_timestamp
                ticker = self._generate_ticker_from_candle(candle, symbol, ticker_timestamp)
                await self.push(symbol, ticker)

    @staticmethod
    def _generate_ticker_from_candle(candle, symbol, last_candle_timestamp):
        return {
            enums.ExchangeConstantsTickersColumns.TIMESTAMP.value: last_candle_timestamp,
            enums.ExchangeConstantsTickersColumns.LAST.value: candle[common_enums.PriceIndexes.IND_PRICE_CLOSE.value],
            enums.ExchangeConstantsTickersColumns.SYMBOL.value: symbol,
            enums.ExchangeConstantsTickersColumns.HIGH.value: candle[common_enums.PriceIndexes.IND_PRICE_HIGH.value],
            enums.ExchangeConstantsTickersColumns.LOW.value: candle[common_enums.PriceIndexes.IND_PRICE_LOW.value],
            enums.ExchangeConstantsTickersColumns.OPEN.value: candle[common_enums.PriceIndexes.IND_PRICE_OPEN.value],
            enums.ExchangeConstantsTickersColumns.CLOSE.value: candle[common_enums.PriceIndexes.IND_PRICE_CLOSE.value],
            enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value:
                candle[common_enums.PriceIndexes.IND_PRICE_VOL.value]
        }

    async def pause(self):
        if self.time_consumer is not None:
            await util.get_time_channel(self).remove_consumer(self.time_consumer)
        self.is_running = False

    async def stop(self):
        await util.stop_and_pause(self)

    async def resume(self):
        if not self.is_running:
            if self.time_consumer is None and not self.channel.is_paused:
                if backtesting_enums.ExchangeDataTables.TICKER in \
                        api.get_available_data_types(self.exchange_data_importer):
                    self.time_consumer = await util.get_time_channel(self).new_consumer(
                        self.handle_timestamp)
                else:
                    await exchanges_channel.get_chan(constants.OHLCV_CHANNEL, self.channel.exchange_manager.id) \
                        .new_consumer(self._ticker_from_ohlcv_callback)
                    self.last_timestamp_pushed_by_symbol = {
                        symbol: 0
                        for symbol in self.channel.exchange_manager.exchange_config.traded_symbol_pairs
                    }
                self.is_running = True
