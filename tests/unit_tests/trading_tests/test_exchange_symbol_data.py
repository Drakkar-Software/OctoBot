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

from random import randint

from config import TimeFrames, PriceIndexes
from octobot_trading.exchanges import SymbolData


class TestExchangeSymbolData:
    def test_update_symbol_candles(self):
        symbol = "BTC/USDT"
        tf_1 = TimeFrames.FIVE_MINUTES
        tf_2 = TimeFrames.ONE_HOUR
        tf_3 = TimeFrames.FOUR_HOURS
        test_inst = SymbolData(symbol)

        fake_candle_1 = self.create_fake_candle(10)
        fake_candle_2 = self.create_fake_candle(11)
        test_inst.update_symbol_candles(tf_1, [fake_candle_1, fake_candle_2], replace_all=True)

        # should be empty
        assert not test_inst.get_candle_data(tf_2)
        assert not test_inst.get_candle_data(tf_3)
        # shouldn't be empty
        assert test_inst.get_candle_data(tf_1)

        candle_data = test_inst.get_candle_data(tf_1)
        # test values
        assert candle_data.get_symbol_close_candles()[-1] == fake_candle_2[PriceIndexes.IND_PRICE_CLOSE.value]
        assert candle_data.get_symbol_open_candles()[-2] == fake_candle_1[PriceIndexes.IND_PRICE_OPEN.value]

        # test update last candle
        fake_candle_3 = self.create_fake_candle(11)
        test_inst.update_symbol_candles(tf_1, fake_candle_3, replace_all=False)
        candle_data = test_inst.get_candle_data(tf_1)
        assert candle_data.get_symbol_close_candles()[-1] == fake_candle_3[PriceIndexes.IND_PRICE_CLOSE.value]
        assert candle_data.get_symbol_high_candles()[-2] == fake_candle_1[PriceIndexes.IND_PRICE_HIGH.value]

        # test new candle
        fake_candle_4 = self.create_fake_candle(20)
        test_inst.update_symbol_candles(tf_1, fake_candle_4, replace_all=False)
        candle_data = test_inst.get_candle_data(tf_1)
        assert candle_data.get_symbol_close_candles()[-1] == fake_candle_4[PriceIndexes.IND_PRICE_CLOSE.value]
        assert candle_data.get_symbol_time_candles()[-1] == fake_candle_4[PriceIndexes.IND_PRICE_TIME.value]
        assert candle_data.get_symbol_volume_candles()[-1] == fake_candle_4[PriceIndexes.IND_PRICE_VOL.value]
        assert candle_data.get_symbol_open_candles()[-1] == fake_candle_4[PriceIndexes.IND_PRICE_OPEN.value]

        # test limit
        fake_candle_5 = self.create_fake_candle(30)
        test_inst.update_symbol_candles(tf_1, fake_candle_5, replace_all=False)
        candle_data = test_inst.get_candle_data(tf_1)
        assert len(candle_data.get_symbol_volume_candles(limit=3)) == 3

        # test lists
        fake_candle_6 = self.create_fake_candle(12)
        test_inst.update_symbol_candles(tf_2, fake_candle_6, replace_all=False)
        fake_candle_7 = self.create_fake_candle(13)
        test_inst.update_symbol_candles(tf_2, fake_candle_7, replace_all=False)
        fake_candle_8 = self.create_fake_candle(12)
        test_inst.update_symbol_candles(tf_3, fake_candle_8, replace_all=True)

        tf2_data = test_inst.get_candle_data(tf_2).get_symbol_close_candles(return_list=True)
        assert tf2_data[-1] == fake_candle_7[PriceIndexes.IND_PRICE_CLOSE.value]
        assert tf2_data[-2] == fake_candle_6[PriceIndexes.IND_PRICE_CLOSE.value]

        tf3_data = test_inst.get_candle_data(tf_3).get_symbol_time_candles(return_list=True)
        assert tf3_data[-1] == fake_candle_8[PriceIndexes.IND_PRICE_TIME.value]

        tf1_data_close = test_inst.get_candle_data(tf_1).get_symbol_close_candles(return_list=True)
        tf1_data_vol = test_inst.get_candle_data(tf_1).get_symbol_volume_candles(return_list=True)
        assert tf1_data_close[-1] == fake_candle_5[PriceIndexes.IND_PRICE_CLOSE.value]
        assert tf1_data_vol[-1] == fake_candle_5[PriceIndexes.IND_PRICE_VOL.value]

        # test replace
        fake_candle_9 = self.create_fake_candle(40)
        test_inst.update_symbol_candles(tf_1, fake_candle_9, replace_all=True)
        tf1_data_low = test_inst.get_candle_data(tf_1).get_symbol_low_candles(return_list=True)
        assert tf1_data_low[-1] == fake_candle_9[PriceIndexes.IND_PRICE_LOW.value]

    def test_max_symbol_candles(self):
        symbol = "BTC/USDT"
        tf = TimeFrames.ONE_DAY
        test_inst = SymbolData(symbol)

        fake_candles = [self.create_fake_candle(i) for i in range(SymbolData.MAX_CANDLES_COUNT)]
        test_inst.update_symbol_candles(tf, fake_candles, replace_all=True)
        assert len(test_inst.get_candle_data(tf).get_symbol_volume_candles()) == SymbolData.MAX_CANDLES_COUNT

        # test to add new one
        fake_candle = self.create_fake_candle(1000)
        test_inst.update_symbol_candles(tf, fake_candle, replace_all=False)
        candle_data = test_inst.get_candle_data(tf)
        assert len(candle_data.get_symbol_volume_candles()) == SymbolData.MAX_CANDLES_COUNT
        assert candle_data.get_symbol_close_candles()[-1] == fake_candle[PriceIndexes.IND_PRICE_CLOSE.value]
        assert candle_data.get_symbol_time_candles()[-1] == fake_candle[PriceIndexes.IND_PRICE_TIME.value]
        assert candle_data.get_symbol_volume_candles()[-1] == fake_candle[PriceIndexes.IND_PRICE_VOL.value]
        assert candle_data.get_symbol_open_candles()[-1] == fake_candle[PriceIndexes.IND_PRICE_OPEN.value]

    @staticmethod
    def create_fake_candle(time):
        return [
            time,
            randint(0, 100),  # open
            randint(0, 100),  # high
            randint(0, 100),  # low
            randint(0, 100),  # close
            randint(0, 100),  # vol
        ]
