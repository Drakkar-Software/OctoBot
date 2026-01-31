#  Drakkar-Software OctoBot-Tentacles
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

import numpy as np
from octobot_commons.data_util import mean

class CandlesUtil:

    @staticmethod
    def HL2(candles_high, candles_low):
        """
        Return a list of HL2 value (high + low ) / 2
        :param high: list of high
        :param low: list of low
        :return: list of HL2
        """
        return np.array(list(map((lambda candles_high, candles_low: mean([candles_high, candles_low])),
                                                                candles_high, candles_low)))

    @staticmethod
    def HLC3(candles_high, candles_low, candles_close):
        """
        Return a list of HLC3 values (high + low + close) / 3
        :param high: list of high
        :param low: list of low
        :param close: list of close
        :return: list of HLC3
        """
        return np.array(list(map((lambda candles_high, candles_low, candles_close:
                            mean([candles_high, candles_low, candles_close])),
                            candles_high, candles_low, candles_close)))

    @staticmethod
    def OHLC4(candles_open, candles_high, candles_low, candles_close):
        """
        Return a list of OHLC4 value (open + high + low + close) / 4
        :param open: list of open
        :param high: list of high
        :param low: list of low
        :param close: list of close
        :return: list of OHLC4
        """
        return np.array(list(map((lambda candles_open, candles_high, candles_low, candles_close:
                            mean([candles_open, candles_high, candles_low, candles_close])),
                            candles_open, candles_high, candles_low, candles_close)))

    @staticmethod
    def HeikinAshi(candles_open, candles_high, candles_low, candles_close):
        """
        Return HeikinAshi array of the given candles
        :param open: list of open
        :param high: list of high
        :param low: list of low
        :param close: list of close
        :return: HAopen, HAhigh, HAlow, HAclose
        """
        haOpen, haHigh, haLow, haClose = [np.array([]) for i in range(4)]
        for i, (open_value, high_value, low_value, close_value) \
                            in enumerate(zip(candles_open, candles_high, candles_low, candles_close)):
            if i == 0:
                haOpen = np.append(haOpen, open_value)
                haHigh = np.append(haHigh, high_value)
                haLow = np.append(haLow, low_value)
                haClose = np.append(haClose, close_value)
                continue
            haOpen = np.append(haOpen, mean([candles_open[i-1], candles_close[i-1]]))
            haHigh = np.append(haHigh, high_value)
            haLow = np.append(haLow, low_value)
            haClose = np.append(haClose, mean([open_value, high_value, low_value, close_value]))
        return haOpen, haHigh, haLow, haClose