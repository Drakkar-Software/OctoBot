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
import octobot_commons.errors as errors

import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchange_data.recent_trades.channel.recent_trade_updater as recent_trade_updater
import octobot_trading.util as util


class RecentTradeUpdaterSimulator(recent_trade_updater.RecentTradeUpdater):
    SIMULATED_RECENT_TRADE_LIMIT = 2

    def __init__(self, channel, importer):
        super().__init__(channel)
        self.exchange_data_importer = importer
        self.exchange_name = self.channel.exchange_manager.exchange_name

        self.last_timestamp_pushed = 0
        self.last_timestamp_pushed_by_symbol = {}
        self.time_consumer = None
        # Only generate recent trades from the shortest handled time frame
        self.recent_trades_time_frame = self.channel.exchange_manager.exchange_config.get_shortest_time_frame().value

    async def start(self):
        await self.resume()

    async def handle_timestamp(self, timestamp, **kwargs):
        try:
            for pair in self.channel.exchange_manager.exchange_config.traded_symbol_pairs:
                recent_trades_data = (await self.exchange_data_importer.get_recent_trades_from_timestamps(
                    exchange_name=self.exchange_name,
                    symbol=pair,
                    inferior_timestamp=timestamp,
                    limit=1))[0]
                if recent_trades_data[0] > self.last_timestamp_pushed:
                    self.last_timestamp_pushed = recent_trades_data[0]
                    await self.push(pair, recent_trades_data[-1])
        except errors.DatabaseNotFoundError as e:
            self.logger.warning(f"Not enough data : {e} will use ohlcv data to simulate recent trades.")
            await self.pause()
            await self.stop()

    async def _recent_trades_from_ohlcv_callback(self, exchange: str, exchange_id: str,
                                                 cryptocurrency: str, symbol: str, time_frame, candle):
        if time_frame == self.recent_trades_time_frame:
            try:
                # Candles are pushed when completed therefore the current price is the candle's close price
                # However we can't only rely on close price to generate minimal recent trades.
                # Recent trades for this candle are between the next candle candle high price and the next candle
                # low price in order to get these prices, use exchange simulator's future candles filled by the
                # previous ohlcv updater cycle that also triggered this call
                future_candle = self.channel.exchange_manager.exchange.get_current_future_candles()[symbol][time_frame]
                last_candle_timestamp = future_candle[common_enums.PriceIndexes.IND_PRICE_TIME.value]
                if last_candle_timestamp > self.last_timestamp_pushed_by_symbol[symbol]:
                    future_candle_low_price = future_candle[common_enums.PriceIndexes.IND_PRICE_LOW.value]
                    future_candle_high_price = future_candle[common_enums.PriceIndexes.IND_PRICE_HIGH.value]
                    recent_trades = [self._generate_recent_trade(last_candle_timestamp, future_candle_low_price),
                                     self._generate_recent_trade(last_candle_timestamp, future_candle_high_price)]
                    self.last_timestamp_pushed_by_symbol[symbol] = last_candle_timestamp
                    await self.push(symbol, recent_trades)
            except (KeyError, TypeError):
                # future candle not initialized or missing, should rarely happen: use received candle's close value
                if candle:
                    last_candle_timestamp = candle[common_enums.PriceIndexes.IND_PRICE_TIME.value]
                    if last_candle_timestamp > self.last_timestamp_pushed_by_symbol[symbol]:
                        last_candle_close_price = candle[common_enums.PriceIndexes.IND_PRICE_CLOSE.value]
                        recent_trades = [self._generate_recent_trade(last_candle_timestamp, last_candle_close_price)] \
                                        * self.SIMULATED_RECENT_TRADE_LIMIT
                        self.last_timestamp_pushed_by_symbol[symbol] = last_candle_timestamp
                        await self.push(symbol, recent_trades)

    @staticmethod
    def _generate_recent_trade(timestamp, price):
        return {
            enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: timestamp,
            enums.ExchangeConstantsOrderColumns.PRICE.value: price
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
                if backtesting_enums.ExchangeDataTables.RECENT_TRADES in \
                        api.get_available_data_types(self.exchange_data_importer):
                    self.time_consumer = await util.get_time_channel(self).new_consumer(
                        self.handle_timestamp)
                else:
                    await exchanges_channel.get_chan(constants.OHLCV_CHANNEL, self.channel.exchange_manager.id) \
                        .new_consumer(self._recent_trades_from_ohlcv_callback)
                    self.last_timestamp_pushed_by_symbol = {
                        symbol: 0
                        for symbol in self.channel.exchange_manager.exchange_config.traded_symbol_pairs
                    }
                self.is_running = True
