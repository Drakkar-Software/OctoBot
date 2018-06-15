import math
import random

import talib
import tulipy
import numpy as np

data = [random.random()*100 for i in range(1000)]

# RSI
data_close = np.array(data)
rsi_v_1 = tulipy.rsi(data_close, period=14)
rsi_v_2 = talib.RSI(data_close)
for rsi in range(len(rsi_v_1)):
    if not math.isnan(rsi_v_2[-rsi]) and round(rsi_v_1[-rsi], 4) != round(rsi_v_2[-rsi], 4):
        print("RSI : failed")
print("RSI : Success")
