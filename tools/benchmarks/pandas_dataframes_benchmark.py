import pandas
import random
import time

from config.cst import *
from tools.data_frame_util import DataFrameUtil


# candle list: time, open, high, low, close, vol
def gen_candle(val, index):
    return [index+1000, val*0.9, val*1.1, val*0.85, val, val/10]


def print_result(description, exec_time, iterations_count, container_size):
    print("{}: {}ms for: {} iterations on a container of {} elements"
          .format(description, exec_time, iterations_count, container_size)
          )


candles = [
    gen_candle(val, int(index))
    for index, val in enumerate([float(100*random.random()) for i in range(50000)])
]

start_time = time.time()
df = DataFrameUtil.candles_array_to_data_frame(candles)
print_result("candles_array_to_data_frame", time.time()-start_time, len(candles), len(df))

new_candles = [
    gen_candle(val, int(index))
    for index, val in enumerate([float(100*random.random()) for i in range(1000)])
]

start_time = time.time()
for c in new_candles:
    df.append(pandas.DataFrame(data=c), ignore_index=True)
print_result("append to df", time.time()-start_time, len(candles), len(df))

start_time = time.time()
for c in new_candles:
    pandas.concat([df,pandas.DataFrame(data=c)], ignore_index=True)
print_result("concat to df", time.time()-start_time, len(candles), len(df))

candles2 = candles
start_time = time.time()
for c in new_candles:
    candles2.append(c)
print_result("append to list", time.time()-start_time, len(candles), len(candles2))


start_time = time.time()
df3 = DataFrameUtil.candles_array_to_data_frame(candles2)
print_result("list to df", time.time()-start_time, len(candles2), len(df3))


mega_candles = [
    gen_candle(val, int(index))
    for index, val in enumerate([float(100*random.random()) for i in range(200000)])
]
start_time = time.time()
df = DataFrameUtil.candles_array_to_data_frame(mega_candles)
print_result("candles_array_to_data_frame", time.time()-start_time, len(mega_candles), len(df))

start_time = time.time()
for c in new_candles:
    pandas.concat([df,pandas.DataFrame(data=c)], ignore_index=True)
print_result("concat to df", time.time()-start_time, len(new_candles), len(df))

start_time = time.time()
for c in new_candles:
    df.loc[len(df)] = c
print_result("add row with loc", time.time()-start_time, len(new_candles), len(df))

start_time = time.time()
for c in new_candles:
    df[PriceStrings.STR_PRICE_VOL.value].iloc[-1] = 8
print_result("EDIT df", time.time()-start_time, len(new_candles), len(df))

start_time = time.time()
for c in new_candles:
    mega_candles[-1][-1] = 8
print_result("EDIT list", time.time()-start_time, len(new_candles), len(mega_candles))

start_time = time.time()
for c in new_candles:
    df.drop(0)
print_result("drop head", time.time()-start_time, len(new_candles), len(df))

start_time = time.time()
for c in new_candles:
    df.drop(0)
    df.reset_index(drop=True, inplace=True)
print_result("drop head with reset-index", time.time()-start_time, len(new_candles), len(df))

start_time = time.time()
for c in new_candles:
    df.drop(0, inplace=True)
    df.reset_index(drop=True, inplace=True)
print_result("inplace drop head with re-index", time.time()-start_time, len(new_candles), len(df))
