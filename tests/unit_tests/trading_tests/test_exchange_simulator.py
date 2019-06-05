#  Drakkar-Software OctoBot
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

import ccxt
import pytest

from config import CONFIG_ENABLED_OPTION, CONFIG_BACKTESTING, TimeFrames, HOURS_TO_SECONDS, PriceIndexes, \
    TraderOrderType, ExchangeConstantsMarketPropertyColumns, FeePropertyColumns, CONFIG_SIMULATOR, \
    CONFIG_SIMULATOR_FEES, CONFIG_SIMULATOR_FEES_MAKER, CONFIG_SIMULATOR_FEES_TAKER, BACKTESTING_DATA_OHLCV, \
    BACKTESTING_DATA_TRADES, ExchangeConstantsOrderColumns
from tests.test_utils.config import load_test_config
from octobot_trading.exchanges import ExchangeManager
from trading.trader.trader_simulator import TraderSimulator


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestExchangeSimulator:
    DEFAULT_SYMBOL = "BTC/USDT"
    DEFAULT_TF = TimeFrames.ONE_HOUR

    @staticmethod
    async def init_default():
        config = load_test_config()
        config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        await exchange_manager.initialize()
        exchange_inst = exchange_manager.get_exchange()
        exchange_simulator = exchange_inst.get_exchange()
        exchange_simulator.init_candles_offset([TimeFrames.ONE_HOUR, TimeFrames.FOUR_HOURS, TimeFrames.ONE_DAY],
                                               TestExchangeSimulator.DEFAULT_SYMBOL)

        trader_inst = TraderSimulator(config, exchange_inst, 1)
        return config, exchange_inst, exchange_simulator, trader_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    async def test_multiple_get_symbol_prices(self):
        _, exchange_inst, _, trader_inst = await self.init_default()
        self.stop(trader_inst)

        first_data = await exchange_inst.get_symbol_prices(
            self.DEFAULT_SYMBOL,
            self.DEFAULT_TF,
            return_list=False)

        second_data = await exchange_inst.get_symbol_prices(
            self.DEFAULT_SYMBOL,
            self.DEFAULT_TF,
            return_list=False)

        # different arrays
        assert first_data is not second_data

        # second is first with DEFAULT_TF difference
        assert first_data[PriceIndexes.IND_PRICE_CLOSE.value][0] == second_data[PriceIndexes.IND_PRICE_CLOSE.value][0]
        assert first_data[PriceIndexes.IND_PRICE_TIME.value][0] == second_data[
            PriceIndexes.IND_PRICE_TIME.value][0]

        # end is end -1 with DEFAULT_TF difference
        assert first_data[PriceIndexes.IND_PRICE_CLOSE.value][-1] == second_data[PriceIndexes.IND_PRICE_CLOSE.value][-2]
        assert first_data[PriceIndexes.IND_PRICE_TIME.value][-1] + HOURS_TO_SECONDS == second_data[
            PriceIndexes.IND_PRICE_TIME.value][-1]

    async def test_get_recent_trades(self):
        _, exchange_inst, _, trader_inst = await self.init_default()
        self.stop(trader_inst)

        await exchange_inst.get_recent_trades(self.DEFAULT_SYMBOL)

    async def test_get_all_currencies_price_ticker(self):
        _, exchange_inst, _, trader_inst = await self.init_default()
        self.stop(trader_inst)

        await exchange_inst.get_all_currencies_price_ticker()

    @staticmethod
    def _assert_fee(fee, currency, price, rate, fee_type):
        assert fee[FeePropertyColumns.CURRENCY.value] == currency
        assert fee[FeePropertyColumns.COST.value] == price
        assert fee[FeePropertyColumns.RATE.value] == rate
        assert fee[FeePropertyColumns.TYPE.value] == fee_type

    async def test_get_trade_fee(self):
        _, exchange_inst, _, _ = await self.init_default()

        # force fees
        exchange_inst.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES] = {
            CONFIG_SIMULATOR_FEES_MAKER: 0.05,
            CONFIG_SIMULATOR_FEES_TAKER: 0.1
        }

        buy_market_fee = exchange_inst.get_trade_fee("BTC/USD", TraderOrderType.BUY_MARKET,
                                                     10, 100, ExchangeConstantsMarketPropertyColumns.TAKER.value)
        self._assert_fee(buy_market_fee, "BTC", 0.01, 0.001, ExchangeConstantsMarketPropertyColumns.TAKER.value)

        sell_market_fee = exchange_inst.get_trade_fee(
            "BTC/USD",  TraderOrderType.SELL_MARKET, 10, 100, ExchangeConstantsMarketPropertyColumns.TAKER.value)
        self._assert_fee(sell_market_fee, "USD", 1, 0.001, ExchangeConstantsMarketPropertyColumns.TAKER.value)

        buy_limit_fee = exchange_inst.get_trade_fee("BTC/USD", TraderOrderType.BUY_LIMIT,
                                                    10, 100, ExchangeConstantsMarketPropertyColumns.MAKER.value)
        self._assert_fee(buy_limit_fee, "BTC", 0.005, 0.0005, ExchangeConstantsMarketPropertyColumns.MAKER.value)

        sell_limit_fee = exchange_inst.get_trade_fee("BTC/USD", TraderOrderType.SELL_LIMIT,
                                                     10, 100, ExchangeConstantsMarketPropertyColumns.TAKER.value)
        self._assert_fee(sell_limit_fee, "USD", 1, 0.001, ExchangeConstantsMarketPropertyColumns.TAKER.value)

    async def test_should_update_data(self):
        _, exchange_inst, exchange_simulator, trader_inst = await self.init_default()

        # first call
        assert exchange_simulator.should_update_data(TimeFrames.ONE_HOUR, self.DEFAULT_SYMBOL)
        assert exchange_simulator.should_update_data(TimeFrames.FOUR_HOURS, self.DEFAULT_SYMBOL)
        assert exchange_simulator.should_update_data(TimeFrames.ONE_DAY, self.DEFAULT_SYMBOL)

        # call get prices
        await exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        await exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        await exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        # call with trader without order
        assert exchange_simulator.should_update_data(TimeFrames.ONE_HOUR, self.DEFAULT_SYMBOL)
        assert not exchange_simulator.should_update_data(TimeFrames.FOUR_HOURS, self.DEFAULT_SYMBOL)
        assert not exchange_simulator.should_update_data(TimeFrames.ONE_DAY, self.DEFAULT_SYMBOL)
        await exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)

        self.stop(trader_inst)

    @staticmethod
    def _get_start_index_for_timeframe(nb_candles, min_limit, timeframe_multiplier):
        return int(nb_candles - (nb_candles-min_limit) / timeframe_multiplier) - 1

    async def test_init_candles_offset(self):
        _, _, exchange_simulator, _ = await self.init_default()

        timeframes = [TimeFrames.THIRTY_MINUTES, TimeFrames.ONE_HOUR, TimeFrames.TWO_HOURS,
                      TimeFrames.FOUR_HOURS, TimeFrames.ONE_DAY]
        exchange_simulator.init_candles_offset(timeframes, self.DEFAULT_SYMBOL)

        offsets = exchange_simulator.time_frames_offset[self.DEFAULT_SYMBOL]
        ohlcv = exchange_simulator.data[self.DEFAULT_SYMBOL][BACKTESTING_DATA_OHLCV]
        assert ohlcv is exchange_simulator.get_ohlcv(self.DEFAULT_SYMBOL)
        nb_candles = len(ohlcv[TimeFrames.THIRTY_MINUTES.value])
        assert offsets[TimeFrames.THIRTY_MINUTES.value] == \
            self._get_start_index_for_timeframe(nb_candles, exchange_simulator.MIN_LIMIT, 1) + 1
        assert offsets[TimeFrames.ONE_HOUR.value] ==  \
            self._get_start_index_for_timeframe(nb_candles, exchange_simulator.MIN_LIMIT, 2)
        assert offsets[TimeFrames.TWO_HOURS.value] ==  \
            self._get_start_index_for_timeframe(nb_candles, exchange_simulator.MIN_LIMIT, 4)
        assert offsets[TimeFrames.FOUR_HOURS.value] ==  \
            self._get_start_index_for_timeframe(nb_candles, exchange_simulator.MIN_LIMIT, 8)
        assert offsets[TimeFrames.ONE_DAY.value] == 244

    async def test_select_trades(self):
        _, _, exchange_simulator, _ = await self.init_default()
        trades = [
            {
                ExchangeConstantsOrderColumns.TIMESTAMP.value: 1549413007896,
                ExchangeConstantsOrderColumns.PRICE.value: "3415.30000"
            },
            {
                ExchangeConstantsOrderColumns.TIMESTAMP.value: 1549413032879,
                ExchangeConstantsOrderColumns.PRICE.value: "3415.30000"
            },
            {
                ExchangeConstantsOrderColumns.TIMESTAMP.value: 1549413032922,
                ExchangeConstantsOrderColumns.PRICE.value: "3415.90000"
            }
        ]
        exchange_simulator.data[self.DEFAULT_SYMBOL][BACKTESTING_DATA_TRADES] = trades
        assert exchange_simulator.select_trades(10, 10, self.DEFAULT_SYMBOL) == []
        assert exchange_simulator.select_trades(1549413007896, -1, self.DEFAULT_SYMBOL) == []
        with pytest.raises(KeyError):
            assert exchange_simulator.select_trades(1549413007.896, 1549413032.879, "ETH/USD") == []
        assert exchange_simulator.select_trades(exchange_simulator.get_uniform_timestamp(1549413007896),
                                                exchange_simulator.get_uniform_timestamp(1549413032879),
                                                self.DEFAULT_SYMBOL) == [
            {
                ExchangeConstantsOrderColumns.TIMESTAMP.value: exchange_simulator.get_uniform_timestamp(1549413007896),
                ExchangeConstantsOrderColumns.PRICE.value: 3415.30000
            },
            {
                ExchangeConstantsOrderColumns.TIMESTAMP.value: exchange_simulator.get_uniform_timestamp(1549413032879),
                ExchangeConstantsOrderColumns.PRICE.value: 3415.30000
            }
        ]
        assert exchange_simulator.select_trades(exchange_simulator.get_uniform_timestamp(1549413007896),
                                                -1, self.DEFAULT_SYMBOL) == [
            {
                ExchangeConstantsOrderColumns.TIMESTAMP.value: exchange_simulator.get_uniform_timestamp(1549413007896),
                ExchangeConstantsOrderColumns.PRICE.value: 3415.30000
            },
            {
                ExchangeConstantsOrderColumns.TIMESTAMP.value: exchange_simulator.get_uniform_timestamp(1549413032879),
                ExchangeConstantsOrderColumns.PRICE.value: 3415.30000
            },
            {
                ExchangeConstantsOrderColumns.TIMESTAMP.value: exchange_simulator.get_uniform_timestamp(1549413032922),
                ExchangeConstantsOrderColumns.PRICE.value: 3415.90000
            }
        ]
