import talib
import tulipy as ti
import numpy as np
import timeit

high_list = [float(i + 2) for i in range(0, 500)]
low_list = [float(i - 2) for i in range(0, 500)]
close_list = [float(i) for i in range(0, 500)]

high_np = np.array(high_list)
low_np = np.array(low_list)
close_np = np.array(close_list)


def test_tulip_stoch():
    ti.stoch(high_np, low_np, close_np, 5, 3, 3)


def test_tulip_rsi():
    ti.rsi(close_np, 14)


def test_tulip_macd():
    ti.macd(close_np, 12, 26, 9)


def test_TA_stoch():
    talib.STOCH(high_np, low_np, close_np, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3,
                slowd_matype=0)


def test_TA_rsi():
    talib.RSI(close_np, timeperiod=14)


def test_TA_macd():
    talib.MACD(close_np, fastperiod=12, slowperiod=26, signalperiod=9)


def print_bench(fct_str, number):
    return "{2}".format(fct_str,
                               number,
                               timeit.timeit("{}()".format(fct_str),
                                             setup="from __main__ import {}".format(fct_str),
                                             number=number))


def print_indic_result(indic_str, tulip_str, ta_str, result_str=None):
    if result_str is None:
        result_str = ""
    try:
        tulipy_perf = float(tulip_str)
        ta_perf = float(ta_str)
        result_str = "{}%".format(tulipy_perf * 100 / ta_perf)
    except ValueError:
        pass

    print("{:>10} | {:^30} | {:^30} | {:^30} ".format(indic_str, tulip_str, ta_str, result_str))


exec_times = 1000
print_indic_result("INDICATOR", "   Tulipy  ", "    TA-LIB  ", "    TI vs TA    ")
print_indic_result("STOCH", print_bench("test_tulip_stoch", exec_times), print_bench("test_TA_stoch", exec_times))
print_indic_result("RSI", print_bench("test_tulip_rsi", exec_times), print_bench("test_TA_rsi", exec_times))
print_indic_result("MACD", print_bench("test_tulip_macd", exec_times), print_bench("test_TA_macd", exec_times))
