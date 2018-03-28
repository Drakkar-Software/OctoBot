"""
Copyright, Rinat Maksutov, 2017.
License: GNU General Public License
"""

import numpy as np
import pandas as pd

"""
Exponential moving average
Source: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:moving_averages
Params: 
    data: pandas DataFrame
    period: smoothing period
    column: the name of the column with values for calculating EMA in the 'data' DataFrame

Returns:
    copy of 'data' DataFrame with 'ema[period]' column added
"""


def ema(data, period=0, column='<CLOSE>'):
    data['ema' + str(period)] = data[column].ewm(ignore_na=False, min_periods=period, com=period, adjust=True).mean()

    return data


"""
Moving Average Convergence/Divergence Oscillator (MACD)
Source: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:moving_average_convergence_divergence_macd
Params: 
    data: pandas DataFrame
    period_long: the longer period EMA (26 days recommended)
    period_short: the shorter period EMA (12 days recommended)
    period_signal: signal line EMA (9 days recommended)
    column: the name of the column with values for calculating MACD in the 'data' DataFrame

Returns:
    copy of 'data' DataFrame with 'macd_val' and 'macd_signal_line' columns added
"""


def macd(data, period_long=26, period_short=12, period_signal=9, column='<CLOSE>'):
    remove_cols = []
    if not 'ema' + str(period_long) in data.columns:
        data = ema(data, period_long, column=column)
        remove_cols.append('ema' + str(period_long))

    if not 'ema' + str(period_short) in data.columns:
        data = ema(data, period_short, column=column)
        remove_cols.append('ema' + str(period_short))

    data['macd_val'] = data['ema' + str(period_short)] - data['ema' + str(period_long)]
    data['macd_signal_line'] = data['macd_val'].ewm(ignore_na=False, min_periods=0, com=period_signal,
                                                    adjust=True).mean()

    data = data.drop(remove_cols, axis=1)

    return data


"""
Accumulation Distribution 
Source: http://stockcharts.com/school/doku.php?st=accumulation+distribution&id=chart_school:technical_indicators:accumulation_distribution_line
Params: 
    data: pandas DataFrame
    trend_periods: the over which to calculate AD
    open_col: the name of the OPEN values column
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column
	close_col: the name of the CLOSE values column
	vol_col: the name of the VOL values column

Returns:
    copy of 'data' DataFrame with 'acc_dist' and 'acc_dist_ema[trend_periods]' columns added
"""


def acc_dist(data, trend_periods=21, open_col='<OPEN>', high_col='<HIGH>', low_col='<LOW>', close_col='<CLOSE>',
             vol_col='<VOL>'):
    for index, row in data.iterrows():
        if row[high_col] != row[low_col]:
            ac = ((row[close_col] - row[low_col]) - (row[high_col] - row[close_col])) / (row[high_col] - row[low_col]) * \
                 row[vol_col]
        else:
            ac = 0
        data.set_value(index, 'acc_dist', ac)
    data['acc_dist_ema' + str(trend_periods)] = data['acc_dist'].ewm(ignore_na=False, min_periods=0, com=trend_periods,
                                                                     adjust=True).mean()

    return data


"""
On Balance Volume (OBV)
Source: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:on_balance_volume_obv
Params: 
    data: pandas DataFrame
    trend_periods: the over which to calculate OBV
	close_col: the name of the CLOSE values column
	vol_col: the name of the VOL values column

Returns:
    copy of 'data' DataFrame with 'obv' and 'obv_ema[trend_periods]' columns added
"""


def on_balance_volume(data, trend_periods=21, close_col='<CLOSE>', vol_col='<VOL>'):
    for index, row in data.iterrows():
        if index > 0:
            last_obv = data.at[index - 1, 'obv']
            if row[close_col] > data.at[index - 1, close_col]:
                current_obv = last_obv + row[vol_col]
            elif row[close_col] < data.at[index - 1, close_col]:
                current_obv = last_obv - row[vol_col]
            else:
                current_obv = last_obv
        else:
            last_obv = 0
            current_obv = row[vol_col]

        data.set_value(index, 'obv', current_obv)

    data['obv_ema' + str(trend_periods)] = data['obv'].ewm(ignore_na=False, min_periods=0, com=trend_periods,
                                                           adjust=True).mean()

    return data


"""
Price-volume trend (PVT) (sometimes volume-price trend)
Source: https://en.wikipedia.org/wiki/Volume%E2%80%93price_trend
Params: 
    data: pandas DataFrame
    trend_periods: the over which to calculate PVT
	close_col: the name of the CLOSE values column
	vol_col: the name of the VOL values column

Returns:
    copy of 'data' DataFrame with 'pvt' and 'pvt_ema[trend_periods]' columns added
"""


def price_volume_trend(data, trend_periods=21, close_col='<CLOSE>', vol_col='<VOL>'):
    for index, row in data.iterrows():
        if index > 0:
            last_val = data.at[index - 1, 'pvt']
            last_close = data.at[index - 1, close_col]
            today_close = row[close_col]
            today_vol = row[vol_col]
            current_val = last_val + (today_vol * (today_close - last_close) / last_close)
        else:
            current_val = row[vol_col]

        data.set_value(index, 'pvt', current_val)

    data['pvt_ema' + str(trend_periods)] = data['pvt'].ewm(ignore_na=False, min_periods=0, com=trend_periods,
                                                           adjust=True).mean()

    return data


"""
Average true range (ATR)
Source: https://en.wikipedia.org/wiki/Average_true_range
Params: 
    data: pandas DataFrame
    trend_periods: the over which to calculate ATR
    open_col: the name of the OPEN values column
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column
	close_col: the name of the CLOSE values column
	vol_col: the name of the VOL values column
	drop_tr: whether to drop the True Range values column from the resulting DataFrame

Returns:
    copy of 'data' DataFrame with 'atr' (and 'true_range' if 'drop_tr' == True) column(s) added
"""


def average_true_range(data, trend_periods=14, open_col='<OPEN>', high_col='<HIGH>', low_col='<LOW>',
                       close_col='<CLOSE>', drop_tr=True):
    for index, row in data.iterrows():
        prices = [row[high_col], row[low_col], row[close_col], row[open_col]]
        if index > 0:
            val1 = np.amax(prices) - np.amin(prices)
            val2 = abs(np.amax(prices) - data.at[index - 1, close_col])
            val3 = abs(np.amin(prices) - data.at[index - 1, close_col])
            true_range = np.amax([val1, val2, val3])

        else:
            true_range = np.amax(prices) - np.amin(prices)

        data.set_value(index, 'true_range', true_range)
    data['atr'] = data['true_range'].ewm(ignore_na=False, min_periods=0, com=trend_periods, adjust=True).mean()
    if drop_tr:
        data = data.drop(['true_range'], axis=1)

    return data


"""
Bollinger Bands
Source: https://en.wikipedia.org/wiki/Bollinger_Bands
Params: 
    data: pandas DataFrame
    trend_periods: the over which to calculate BB
	close_col: the name of the CLOSE values column

Returns:
    copy of 'data' DataFrame with 'bol_bands_middle', 'bol_bands_upper' and 'bol_bands_lower' columns added
"""


def bollinger_bands(data, trend_periods=20, close_col='<CLOSE>'):
    data['bol_bands_middle'] = data[close_col].ewm(ignore_na=False, min_periods=0, com=trend_periods,
                                                   adjust=True).mean()
    for index, row in data.iterrows():

        s = data[close_col].iloc[index - trend_periods: index]
        sums = 0
        middle_band = data.at[index, 'bol_bands_middle']
        for e in s:
            sums += np.square(e - middle_band)

        std = np.sqrt(sums / trend_periods)
        d = 2
        upper_band = middle_band + (d * std)
        lower_band = middle_band - (d * std)

        data.set_value(index, 'bol_bands_upper', upper_band)
        data.set_value(index, 'bol_bands_lower', lower_band)

    return data


"""
Chaikin Oscillator
Source: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:chaikin_oscillator
Params: 
    data: pandas DataFrame
	periods_short: period for the shorter EMA (3 days recommended)
	periods_long: period for the longer EMA (10 days recommended)
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column
	close_col: the name of the CLOSE values column
	vol_col: the name of the VOL values column

Returns:
    copy of 'data' DataFrame with 'ch_osc' column added
"""


def chaikin_oscillator(data, periods_short=3, periods_long=10, high_col='<HIGH>',
                       low_col='<LOW>', close_col='<CLOSE>', vol_col='<VOL>'):
    ac = pd.Series([])

    for index, row in data.iterrows():
        if row[high_col] != row[low_col]:
            val = ((row[close_col] - row[low_col]) - (row[high_col] - row[close_col])) / (
                    row[high_col] - row[low_col]) * row[vol_col]
        else:
            val = 0
        ac.set_value(index, val)

    ema_long = ac.ewm(ignore_na=False, min_periods=0, com=periods_long, adjust=True).mean()
    ema_short = ac.ewm(ignore_na=False, min_periods=0, com=periods_short, adjust=True).mean()
    data['ch_osc'] = ema_short - ema_long

    return data


"""
Typical Price
Source: https://en.wikipedia.org/wiki/Typical_price
Params: 
    data: pandas DataFrame
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column
	close_col: the name of the CLOSE values column

Returns:
    copy of 'data' DataFrame with 'typical_price' column added
"""


def typical_price(data, high_col='<HIGH>', low_col='<LOW>', close_col='<CLOSE>'):
    data['typical_price'] = (data[high_col] + data[low_col] + data[close_col]) / 3

    return data


"""
Ease of Movement
Source: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:ease_of_movement_emv
Params: 
    data: pandas DataFrame
	period: period for calculating EMV
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column
	vol_col: the name of the VOL values column

Returns:
    copy of 'data' DataFrame with 'emv' and 'emv_ema_[period]' columns added
"""


def ease_of_movement(data, period=14, high_col='<HIGH>', low_col='<LOW>', vol_col='<VOL>'):
    for index, row in data.iterrows():
        if index > 0:
            midpoint_move = (row[high_col] + row[low_col]) / 2 - (
                    data.at[index - 1, high_col] + data.at[index - 1, low_col]) / 2
        else:
            midpoint_move = 0

        diff = row[high_col] - row[low_col]

        if diff == 0:
            # this is to avoid division by zero below
            diff = 0.000000001

        vol = row[vol_col]
        if vol == 0:
            vol = 1
        box_ratio = (vol / 100000000) / (diff)
        emv = midpoint_move / box_ratio

        data.set_value(index, 'emv', emv)

    data['emv_ema_' + str(period)] = data['emv'].ewm(ignore_na=False, min_periods=0, com=period, adjust=True).mean()

    return data


"""
Mass Index
Source: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:mass_index
Params: 
    data: pandas DataFrame
	period: period for calculating MI (9 days recommended)
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column

Returns:
    copy of 'data' DataFrame with 'mass_index' column added
"""


def mass_index(data, period=25, ema_period=9, high_col='<HIGH>', low_col='<LOW>'):
    high_low = data[high_col] - data[low_col] + 0.000001  # this is to avoid division by zero below
    ema = high_low.ewm(ignore_na=False, min_periods=0, com=ema_period, adjust=True).mean()
    ema_ema = ema.ewm(ignore_na=False, min_periods=0, com=ema_period, adjust=True).mean()
    div = ema / ema_ema

    for index, row in data.iterrows():
        if index >= period:
            val = div[index - 25:index].sum()
        else:
            val = 0
        data.set_value(index, 'mass_index', val)

    return data


"""
Average directional movement index
Source: https://en.wikipedia.org/wiki/Average_directional_movement_index
Params: 
    data: pandas DataFrame
	periods: period for calculating ADX (14 days recommended)
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column

Returns:
    copy of 'data' DataFrame with 'adx', 'dxi', 'di_plus', 'di_minus' columns added
"""


def directional_movement_index(data, periods=14, high_col='<HIGH>', low_col='<LOW>'):
    remove_tr_col = False
    if not 'true_range' in data.columns:
        data = average_true_range(data, drop_tr=False)
        remove_tr_col = True

    data['m_plus'] = 0.
    data['m_minus'] = 0.

    for i, row in data.iterrows():
        if i > 0:
            data.set_value(i, 'm_plus', row[high_col] - data.at[i - 1, high_col])
            data.set_value(i, 'm_minus', row[low_col] - data.at[i - 1, low_col])

    data['dm_plus'] = 0.
    data['dm_minus'] = 0.

    for i, row in data.iterrows():
        if row['m_plus'] > row['m_minus'] and row['m_plus'] > 0:
            data.set_value(i, 'dm_plus', row['m_plus'])

        if row['m_minus'] > row['m_plus'] and row['m_minus'] > 0:
            data.set_value(i, 'dm_minus', row['m_minus'])

    data['di_plus'] = (data['dm_plus'] / data['true_range']).ewm(ignore_na=False, min_periods=0, com=periods,
                                                                 adjust=True).mean()
    data['di_minus'] = (data['dm_minus'] / data['true_range']).ewm(ignore_na=False, min_periods=0, com=periods,
                                                                   adjust=True).mean()

    data['dxi'] = np.abs(data['di_plus'] - data['di_minus']) / (data['di_plus'] + data['di_minus'])
    data.set_value(0, 'dxi', 1.)
    data['adx'] = data['dxi'].ewm(ignore_na=False, min_periods=0, com=periods, adjust=True).mean()
    data = data.drop(['m_plus', 'm_minus', 'dm_plus', 'dm_minus'], axis=1)
    if remove_tr_col:
        data = data.drop(['true_range'], axis=1)

    return data


"""
Money Flow Index (MFI)
Source: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:money_flow_index_mfi
Params: 
    data: pandas DataFrame
	periods: period for calculating MFI (14 days recommended)
	vol_col: the name of the VOL values column

Returns:
    copy of 'data' DataFrame with 'money_flow_index' column added
"""


def money_flow_index(data, periods=14, vol_col='<VOL>'):
    remove_tp_col = False
    if not 'typical_price' in data.columns:
        data = typical_price(data)
        remove_tp_col = True

    data['money_flow'] = data['typical_price'] * data[vol_col]
    data['money_ratio'] = 0.
    data['money_flow_index'] = 0.
    data['money_flow_positive'] = 0.
    data['money_flow_negative'] = 0.

    for index, row in data.iterrows():
        if index > 0:
            if row['typical_price'] < data.at[index - 1, 'typical_price']:
                data.set_value(index, 'money_flow_positive', row['money_flow'])
            else:
                data.set_value(index, 'money_flow_negative', row['money_flow'])

        if index >= periods:
            period_slice = data['money_flow'][index - periods:index]
            positive_sum = data['money_flow_positive'][index - periods:index].sum()
            negative_sum = data['money_flow_negative'][index - periods:index].sum()

            if negative_sum == 0.:
                # this is to avoid division by zero below
                negative_sum = 0.00001
            m_r = positive_sum / negative_sum

            mfi = 1 - (1 / (1 + m_r))

            data.set_value(index, 'money_ratio', m_r)
            data.set_value(index, 'money_flow_index', mfi)

    data = data.drop(['money_flow', 'money_ratio', 'money_flow_positive', 'money_flow_negative'], axis=1)

    if remove_tp_col:
        data = data.drop(['typical_price'], axis=1)

    return data


"""
Negative Volume Index (NVI)
Source: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:negative_volume_inde
Params: 
    data: pandas DataFrame
	periods: period for calculating NVI (255 days recommended)
	close_col: the name of the CLOSE values column
	vol_col: the name of the VOL values column

Returns:
    copy of 'data' DataFrame with 'nvi' and 'nvi_ema' columns added
"""


def negative_volume_index(data, periods=255, close_col='<CLOSE>', vol_col='<VOL>'):
    data['nvi'] = 0.

    for index, row in data.iterrows():
        if index > 0:
            prev_nvi = data.at[index - 1, 'nvi']
            prev_close = data.at[index - 1, close_col]
            if row[vol_col] < data.at[index - 1, vol_col]:
                nvi = prev_nvi + (row[close_col] - prev_close / prev_close * prev_nvi)
            else:
                nvi = prev_nvi
        else:
            nvi = 1000
        data.set_value(index, 'nvi', nvi)
    data['nvi_ema'] = data['nvi'].ewm(ignore_na=False, min_periods=0, com=periods, adjust=True).mean()

    return data


"""
Positive Volume Index (PVI)
Source: https://www.equities.com/news/the-secret-to-the-positive-volume-index
Params: 
    data: pandas DataFrame
	periods: period for calculating PVI (255 days recommended)
	close_col: the name of the CLOSE values column
	vol_col: the name of the VOL values column

Returns:
    copy of 'data' DataFrame with 'pvi' and 'pvi_ema' columns added
"""


def positive_volume_index(data, periods=255, close_col='<CLOSE>', vol_col='<VOL>'):
    data['pvi'] = 0.

    for index, row in data.iterrows():
        if index > 0:
            prev_pvi = data.at[index - 1, 'pvi']
            prev_close = data.at[index - 1, close_col]
            if row[vol_col] > data.at[index - 1, vol_col]:
                pvi = prev_pvi + (row[close_col] - prev_close / prev_close * prev_pvi)
            else:
                pvi = prev_pvi
        else:
            pvi = 1000
        data.set_value(index, 'pvi', pvi)
    data['pvi_ema'] = data['pvi'].ewm(ignore_na=False, min_periods=0, com=periods, adjust=True).mean()

    return data


"""
Momentum
Source: https://en.wikipedia.org/wiki/Momentum_(technical_analysis)
Params: 
    data: pandas DataFrame
	periods: period for calculating momentum
	close_col: the name of the CLOSE values column

Returns:
    copy of 'data' DataFrame with 'momentum' column added
"""


def momentum(data, periods=14, close_col='<CLOSE>'):
    data['momentum'] = 0.

    for index, row in data.iterrows():
        if index >= periods:
            prev_close = data.at[index - periods, close_col]
            val_perc = (row[close_col] - prev_close) / prev_close

            data.set_value(index, 'momentum', val_perc)

    return data


"""
Relative Strenght Index
Source: https://en.wikipedia.org/wiki/Relative_strength_index
Params: 
    data: pandas DataFrame
	periods: period for calculating momentum
	close_col: the name of the CLOSE values column

Returns:
    copy of 'data' DataFrame with 'rsi' column added
"""


def rsi(data, periods=14, close_col='<CLOSE>'):
    data['rsi_u'] = 0.
    data['rsi_d'] = 0.
    data['rsi'] = 0.

    for index, row in data.iterrows():
        if index >= periods:

            prev_close = data.at[index - periods, close_col]
            if prev_close < row[close_col]:
                data.set_value(index, 'rsi_u', row[close_col] - prev_close)
            elif prev_close > row[close_col]:
                data.set_value(index, 'rsi_d', prev_close - row[close_col])

    data['rsi'] = data['rsi_u'].ewm(ignore_na=False, min_periods=0, com=periods, adjust=True).mean() / (
            data['rsi_u'].ewm(ignore_na=False, min_periods=0, com=periods, adjust=True).mean() + data['rsi_d'].ewm(
        ignore_na=False, min_periods=0, com=periods, adjust=True).mean())

    data = data.drop(['rsi_u', 'rsi_d'], axis=1)

    return data


"""
Chaikin Volatility (CV)
Source: https://www.marketvolume.com/technicalanalysis/chaikinvolatility.asp
Params: 
    data: pandas DataFrame
	ema_periods: period for smoothing Highest High and Lowest Low difference
	change_periods: the period for calculating the difference between Highest High and Lowest Low
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column
	close_col: the name of the CLOSE values column

Returns:
    copy of 'data' DataFrame with 'chaikin_volatility' column added
"""


def chaikin_volatility(data, ema_periods=10, change_periods=10, high_col='<HIGH>', low_col='<LOW>',
                       close_col='<CLOSE>'):
    data['ch_vol_hl'] = data[high_col] - data[low_col]
    data['ch_vol_ema'] = data['ch_vol_hl'].ewm(ignore_na=False, min_periods=0, com=ema_periods, adjust=True).mean()
    data['chaikin_volatility'] = 0.

    for index, row in data.iterrows():
        if index >= change_periods:

            prev_value = data.at[index - change_periods, 'ch_vol_ema']
            if prev_value == 0:
                # this is to avoid division by zero below
                prev_value = 0.0001
            data.set_value(index, 'chaikin_volatility', ((row['ch_vol_ema'] - prev_value) / prev_value))

    data = data.drop(['ch_vol_hl', 'ch_vol_ema'], axis=1)

    return data


"""
William's Accumulation/Distribution
Source: https://www.metastock.com/customer/resources/taaz/?p=125
Params: 
    data: pandas DataFrame
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column
	close_col: the name of the CLOSE values column

Returns:
    copy of 'data' DataFrame with 'williams_ad' column added
"""


def williams_ad(data, high_col='<HIGH>', low_col='<LOW>', close_col='<CLOSE>'):
    data['williams_ad'] = 0.

    for index, row in data.iterrows():
        if index > 0:
            prev_value = data.at[index - 1, 'williams_ad']
            prev_close = data.at[index - 1, close_col]
            if row[close_col] > prev_close:
                ad = row[close_col] - min(prev_close, row[low_col])
            elif row[close_col] < prev_close:
                ad = row[close_col] - max(prev_close, row[high_col])
            else:
                ad = 0.

            data.set_value(index, 'williams_ad', (ad + prev_value))

    return data


"""
William's % R
Source: https://www.metastock.com/customer/resources/taaz/?p=126
Params: 
    data: pandas DataFrame
	periods: the period over which to calculate the indicator value
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column
	close_col: the name of the CLOSE values column

Returns:
    copy of 'data' DataFrame with 'williams_r' column added
"""


def williams_r(data, periods=14, high_col='<HIGH>', low_col='<LOW>', close_col='<CLOSE>'):
    data['williams_r'] = 0.

    for index, row in data.iterrows():
        if index > periods:
            data.set_value(index, 'williams_r', ((max(data[high_col][index - periods:index]) - row[close_col]) /
                                                 (max(data[high_col][index - periods:index]) - min(
                                                     data[low_col][index - periods:index]))))

    return data


"""
TRIX
Source: https://www.metastock.com/customer/resources/taaz/?p=114
Params: 
    data: pandas DataFrame
	periods: the period over which to calculate the indicator value
	signal_periods: the period for signal moving average
	close_col: the name of the CLOSE values column

Returns:
    copy of 'data' DataFrame with 'trix' and 'trix_signal' columns added
"""


def trix(data, periods=14, signal_periods=9, close_col='<CLOSE>'):
    data['trix'] = data[close_col].ewm(ignore_na=False, min_periods=0, com=periods, adjust=True).mean()
    data['trix'] = data['trix'].ewm(ignore_na=False, min_periods=0, com=periods, adjust=True).mean()
    data['trix'] = data['trix'].ewm(ignore_na=False, min_periods=0, com=periods, adjust=True).mean()
    data['trix_signal'] = data['trix'].ewm(ignore_na=False, min_periods=0, com=signal_periods, adjust=True).mean()

    return data


"""
Ultimate Oscillator
Source: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:ultimate_oscillator
Params: 
    data: pandas DataFrame
	period_1: the period of the first average (7 days recommended)
	period_2: the period of the second average (14 days recommended)
	period_3: the period of the third average (28 days recommended)
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column
	close_col: the name of the CLOSE values column

Returns:
    copy of 'data' DataFrame with 'ultimate_oscillator' column added
"""


def ultimate_oscillator(data, period_1=7, period_2=14, period_3=28, high_col='<HIGH>', low_col='<LOW>',
                        close_col='<CLOSE>'):
    data['ultimate_oscillator'] = 0.
    data['uo_bp'] = 0.
    data['uo_tr'] = 0.
    data['uo_avg_1'] = 0.
    data['uo_avg_2'] = 0.
    data['uo_avg_3'] = 0.

    for index, row in data.iterrows():
        if index > 0:

            bp = row[close_col] - min(row[low_col], data.at[index - 1, close_col])
            tr = max(row[high_col], data.at[index - 1, close_col]) - min(row[low_col], data.at[index - 1, close_col])

            data.set_value(index, 'uo_bp', bp)
            data.set_value(index, 'uo_tr', tr)
            if index >= period_1:
                uo_avg_1 = sum(data['uo_bp'][index - period_1:index]) / sum(data['uo_tr'][index - period_1:index])
                data.set_value(index, 'uo_avg_1', uo_avg_1)
            if index >= period_2:
                uo_avg_2 = sum(data['uo_bp'][index - period_2:index]) / sum(data['uo_tr'][index - period_2:index])
                data.set_value(index, 'uo_avg_2', uo_avg_2)
            if index >= period_3:
                uo_avg_3 = sum(data['uo_bp'][index - period_3:index]) / sum(data['uo_tr'][index - period_3:index])
                data.set_value(index, 'uo_avg_3', uo_avg_3)
                uo = (4 * uo_avg_1 + 2 * uo_avg_2 + uo_avg_3) / 7
                data.set_value(index, 'ultimate_oscillator', uo)

    data = data.drop(['uo_bp', 'uo_tr', 'uo_avg_1', 'uo_avg_2', 'uo_avg_3'], axis=1)

    return data
