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

from tentacles.Evaluator.Util import CandlesUtil


def test_HL2():
    candles_high = np.array([10, 12, np.nan, 45, 5.67, 6.54, 75, 8.01, 9])
    candles_low = np.array([9, 8, 7, 6, 5, 4, 3, 2, 1])
    np.testing.assert_array_equal(CandlesUtil.HL2(candles_high, candles_low),
                                  np.array([9.5, 10, np.nan, 25.5, 5.335, 5.27, 39.0, 5.005, 5.0], dtype=np.float64))

    candles_high = np.array([120, 123, 54, 45, 210.54, 546.21, 981.2, .958, 65.7])
    candles_low = np.array([887.592, 896.519, 97.416, 233.987, 846.789, 713.054, 856.985, 421.17, 874.296])
    np.testing.assert_array_equal(CandlesUtil.HL2(candles_high, candles_low),
                                    np.array([503.796, 509.7595, 75.708, 139.49349999999998, 528.6645, 629.6320000000001,
                                    919.0925, 211.06400000000002, 469.99800000000005], dtype=np.float64))

def test_HLC3():
    candles_high = np.array([9, 13, np.nan, 45, 5.67, 6.54, 75, 8.01, 9])
    candles_low = np.array([19, 25, 17, 36, 45, 84, 31, 21, 10])
    candles_close = np.array([2, 4, 4, 4, 6, 7, 8, 9, 10])
    np.testing.assert_array_equal(CandlesUtil.HLC3(candles_high, candles_low, candles_close),
                                  np.array([10, 14, np.nan, 28.333333333333332, 18.89,
                                  32.513333333333335, 38, 12.67, 9.666666666666666], dtype=np.float64))

    candles_high = np.array([733.985, 86.751, 388.834, 630.849, 231.102, 224.815, 430.74, 776.919, 209.207])
    candles_low = np.array([145.747, 829.698, 534.426, 879.53, 187.895, 698.515, 822.942, 532.641, 626.917])
    candles_close = np.array([811.199, 278.313, 817.295, 315.199, 974.104, 775.321, 979.139, 790.477, 518.736])
    np.testing.assert_array_equal(CandlesUtil.HLC3(candles_high, candles_low, candles_close),
                                  np.array([563.6436666666667, 398.25399999999996, 580.185, 608.526, 464.367,
                                  566.217, 744.2736666666666, 700.0123333333332, 451.62000000000006], dtype=np.float64))

def test_OHLC4():
    candles_open = np.array([251.613, 259.098, 247.819, 140.73, 237.547, 830.611, 433.168, 404.026, 403.538])
    candles_high = np.array([980.99, 403.92, 698.072, 658.647, 245.151, 480.9, 621.35, 429.109, 637.439])
    candles_low = np.array([658.777, 101.13, 549.588, 28.624, 132.07, 813.572, 366.478, 619.649, 371.696])
    candles_close = np.array([812.829, 880.456, 406.039, 39.224, 917.386, 707.281, 737.851, 330.262, 258.689])
    np.testing.assert_array_equal(CandlesUtil.OHLC4(candles_open, candles_high, candles_low, candles_close),
                                    np.array([676.05225, 411.151, 475.37949999999995, 216.80625000000003,
                                    383.0385, 708.091, 539.71175, 445.7615, 417.84049999999996], dtype=np.float64))

    candles_open = np.array([345.468, 484.778, 332.855, 401.893, 41.936, 333.738, 983.158, 996.979, 807.855])
    candles_high = np.array([547.277, 856.206, 439.542, 921.475, 778.994, 156.285, 653.31, 534.865, 427.64])
    candles_low = np.array([328.444, 593.535, 4.243, 83.902, 811.859, 396.442, 433.552, 127.624, 314.613])
    candles_close = np.array([905.792, 382.98, 135.529, 494.942, 510.52, 399.78, 897.088, 192.068, 771.189])
    np.testing.assert_array_equal(CandlesUtil.OHLC4(candles_open, candles_high, candles_low, candles_close),
                                        np.array([531.74525, 579.37475, 228.04225, 475.553, 535.82725,
                                        321.56125, 741.777, 462.884, 580.32425], dtype=np.float64))

def test_HeikinAshi():
    candles_open = np.array([977.88, 573.634, 816.233, 846.748, 184.114, 35.742, 598.653, 745.916, 854.334])
    candles_high = np.array([4.757, 499.759, 602.794, 179.313, 802.019, 384.307, 637.378, 161.048, 366.51])
    candles_low = np.array([903.152, 877.832, 966.154, 104.582, 837.638, 568.788, 788.584, 510.926, 608.184])
    candles_close = np.array([405.527, 685.962, 495.698, 271.687, 573.667, 891.018, 445.342, 344.928, 894.279])

    haOpen, haHigh, haLow, haClose = CandlesUtil.HeikinAshi(candles_open, candles_high, candles_low, candles_close)
    np.testing.assert_array_equal(haOpen, np.array([977.88, 691.7035, 629.798, 655.9655, 559.2175,
                                                378.89050000000003, 463.38, 521.9975, 545.422], dtype=np.float64))
    np.testing.assert_array_equal(haHigh, np.array([4.757, 499.759, 602.794, 179.313, 802.019,
                                                384.307, 637.378, 161.048, 366.51], dtype=np.float64))
    np.testing.assert_array_equal(haLow, np.array([903.152, 877.832, 966.154, 104.582, 837.638,
                                                568.788, 788.584, 510.926, 608.184], dtype=np.float64))
    np.testing.assert_array_equal(haClose, np.array([405.527, 659.29675, 720.21975, 350.5825, 599.3595,
                                                469.96375, 617.48925, 440.70450000000005, 680.82675], dtype=np.float64))

    candles_open = np.array([188.539, 334.682, 495.604, 638.736, 632.213, 705.675, 876.735, 69.951, 909.477])
    candles_high = np.array([259.316, 843.705, 170.388, 318.961, 918.236, 585.595, 23.266, 657.422, 270.557])
    candles_low = np.array([652.361, 293.607, 295.191, 893.255, 819.447, 647.016, 330.303, 472.415, 617.705])
    candles_close = np.array([968.007, 114.792, 680.216, 168.147, 478.577, 437.676, 299.474, 208.601, 333.237])

    haOpen, haHigh, haLow, haClose = CandlesUtil.HeikinAshi(candles_open, candles_high, candles_low, candles_close)
    np.testing.assert_array_equal(haOpen, np.array([188.539, 578.2729999999999, 224.73700000000002, 587.91,
                                                403.4415, 555.395, 571.6754999999999, 588.1045, 139.276], dtype=np.float64))
    np.testing.assert_array_equal(haHigh, np.array([259.316, 843.705, 170.388, 318.961, 918.236, 585.595,
                                                23.266, 657.422, 270.557], dtype=np.float64))
    np.testing.assert_array_equal(haLow, np.array([652.361, 293.607, 295.191, 893.255, 819.447, 647.016,
                                                330.303, 472.415, 617.705], dtype=np.float64))
    np.testing.assert_array_equal(haClose, np.array([968.007, 396.6965, 410.34975, 504.77475, 712.11825,
                                                593.9905, 382.4445, 352.09725000000003, 532.744], dtype=np.float64))