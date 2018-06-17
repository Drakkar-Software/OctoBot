import random
import time

import pandas

from config.cst import *


# Candles to dataframe
def candles_array_to_data_frame(candles_array):
    prices = {PriceStrings.STR_PRICE_HIGH.value: [],
              PriceStrings.STR_PRICE_LOW.value: [],
              PriceStrings.STR_PRICE_OPEN.value: [],
              PriceStrings.STR_PRICE_CLOSE.value: [],
              PriceStrings.STR_PRICE_VOL.value: [],
              PriceStrings.STR_PRICE_TIME.value: []}

    for c in candles_array:
        prices[PriceStrings.STR_PRICE_TIME.value].append(float(c[PriceIndexes.IND_PRICE_TIME.value]))
        prices[PriceStrings.STR_PRICE_OPEN.value].append(float(c[PriceIndexes.IND_PRICE_OPEN.value]))
        prices[PriceStrings.STR_PRICE_HIGH.value].append(float(c[PriceIndexes.IND_PRICE_HIGH.value]))
        prices[PriceStrings.STR_PRICE_LOW.value].append(float(c[PriceIndexes.IND_PRICE_LOW.value]))
        prices[PriceStrings.STR_PRICE_CLOSE.value].append(float(c[PriceIndexes.IND_PRICE_CLOSE.value]))
        prices[PriceStrings.STR_PRICE_VOL.value].append(float(c[PriceIndexes.IND_PRICE_VOL.value]))

    return pandas.DataFrame(data=prices)


# candle list: time, open, high, low, close, vol
def gen_candle(val, index):
    return [index + 1000, val * 0.9, val * 1.1, val * 0.85, val, val / 10]


def print_result(description, exec_time, iterations_count, container_size):
    print("{}: {}ms for: {} iterations on a container of {} elements"
          .format(description, exec_time, iterations_count, container_size)
          )


candles = [
    gen_candle(val, int(index))
    for index, val in enumerate([float(100 * random.random()) for i in range(50000)])
]

start_time = time.time()
df = candles_array_to_data_frame(candles)
print_result("candles_array_to_data_frame", time.time() - start_time, len(candles), len(df))

new_candles = [
    gen_candle(val, int(index))
    for index, val in enumerate([float(100 * random.random()) for _ in range(1000)])
]

start_time = time.time()
for c in new_candles:
    df.append(pandas.DataFrame(data=c), ignore_index=True)
print_result("append to df", time.time() - start_time, len(candles), len(df))

start_time = time.time()
for c in new_candles:
    pandas.concat([df, pandas.DataFrame(data=c)], ignore_index=True)
print_result("concat to df", time.time() - start_time, len(candles), len(df))

candles2 = candles
start_time = time.time()
for c in new_candles:
    candles2.append(c)
print_result("append to list", time.time() - start_time, len(candles), len(candles2))

start_time = time.time()
df3 = candles_array_to_data_frame(candles2)
print_result("list to df", time.time() - start_time, len(candles2), len(df3))

mega_candles = [
    gen_candle(val, int(index))
    for index, val in enumerate([float(100 * random.random()) for _ in range(200000)])
]
start_time = time.time()
df = candles_array_to_data_frame(mega_candles)
print_result("candles_array_to_data_frame", time.time() - start_time, len(mega_candles), len(df))

start_time = time.time()
for c in new_candles:
    pandas.concat([df, pandas.DataFrame(data=c)], ignore_index=True)
print_result("concat to df", time.time() - start_time, len(new_candles), len(df))

start_time = time.time()
for c in new_candles:
    df.loc[len(df)] = c
print_result("add row with loc", time.time() - start_time, len(new_candles), len(df))

start_time = time.time()
for c in new_candles:
    df[PriceStrings.STR_PRICE_VOL.value].iloc[-1] = 8
print_result("EDIT df", time.time() - start_time, len(new_candles), len(df))

start_time = time.time()
for c in new_candles:
    mega_candles[-1][-1] = 8
print_result("EDIT list", time.time() - start_time, len(new_candles), len(mega_candles))

start_time = time.time()
for c in new_candles:
    df.drop(0)
print_result("drop head", time.time() - start_time, len(new_candles), len(df))

start_time = time.time()
for c in new_candles:
    df.drop(0)
    df.reset_index(drop=True, inplace=True)
print_result("drop head with reset-index", time.time() - start_time, len(new_candles), len(df))

start_time = time.time()
for c in new_candles:
    df.drop(0, inplace=True)
    df.reset_index(drop=True, inplace=True)
print_result("inplace drop head with re-index", time.time() - start_time, len(new_candles), len(df))
