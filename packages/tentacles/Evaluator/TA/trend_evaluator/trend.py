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
import math

import tulipy
import numpy

import octobot_commons.constants as commons_constants
import octobot_commons.enums as enums
import octobot_commons.data_util as data_util
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.util as evaluators_util
import octobot_trading.api as trading_api
import tentacles.Evaluator.Util as EvaluatorUtil


class SuperTrendEvaluator(evaluators.TAEvaluator):
    FACTOR = "factor"
    LENGTH = "length"
    PREV_UPPER_BAND = "prev_upper_band"
    PREV_LOWER_BAND = "prev_lower_band"
    PREV_SUPERTREND = "prev_supertrend"
    PREV_ATR = "prev_atr"

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.factor = 3
        self.length = 10
        self.reversals_only = False
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        self.previous_value = {}

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the evaluator, should define all the evaluator's user inputs
        """
        self.factor = self.UI.user_input("factor", enums.UserInputTypes.FLOAT, self.factor,
                                         inputs, min_val=0, title="Factor multiplier of the ATR")
        self.length = self.UI.user_input("length", enums.UserInputTypes.INT, self.length,
                                         inputs, min_val=1, title="Length of the ATR")
        self.reversals_only = self.UI.user_input(
            "reversals_only", enums.UserInputTypes.BOOLEAN, self.reversals_only, inputs, 
            title="Reversals only: evaluates -1 and 1 only on trend reversals, 0 otherwise"
        )

    async def ohlcv_callback(self, exchange: str, exchange_id: str, cryptocurrency: str,
                             symbol: str, time_frame, candle, inc_in_construction_data):
        exchange_symbol_data = self.get_exchange_symbol_data(exchange, exchange_id, symbol)
        high = trading_api.get_symbol_high_candles(exchange_symbol_data, time_frame,
                                                   include_in_construction=inc_in_construction_data)
        low = trading_api.get_symbol_low_candles(exchange_symbol_data, time_frame,
                                                 include_in_construction=inc_in_construction_data)
        close = trading_api.get_symbol_close_candles(exchange_symbol_data, time_frame,
                                                     include_in_construction=inc_in_construction_data)
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        if len(close) > self.length:
            await self.evaluate(cryptocurrency, symbol, time_frame, candle, high, low, close)
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))

    async def evaluate(self, cryptocurrency, symbol, time_frame, candle, high, low, close):
        hl2 = EvaluatorUtil.CandlesUtil.HL2(high, low)[-1]
        atr = tulipy.atr(high, low, close, self.length)[-1]

        previous_value = self.get_previous_value(symbol, time_frame)

        upper_band = hl2 + self.factor * atr
        lower_band = hl2 - self.factor * atr
        prev_upper_band = previous_value.get(self.PREV_UPPER_BAND, 0)
        prev_lower_band = previous_value.get(self.PREV_LOWER_BAND, 0)

        # compute latest lower and upper band values
        latest_lower_band = lower_band if (lower_band > prev_lower_band or close[-2] < prev_lower_band) else prev_lower_band
        latest_upper_band = upper_band if (upper_band < prev_upper_band or close[-2] > prev_upper_band) else prev_upper_band

        prev_super_trend = previous_value.get(self.PREV_SUPERTREND, 0)

        signal = -1
        is_reversal = False
        if previous_value.get(self.PREV_ATR, None) is None:
            # not enough data to compute supertrend evaluation
            signal = -1
        else:
            # there is a previous value: check if the latest close is above or below ATR
            # and select the correct band to use
            if prev_super_trend == prev_upper_band:
                # previous bearish trend: previous super trend used the upper band 
                # bullish if the latest close is above latest upper band
                bullish_switch = close[-1] > latest_upper_band
                if bullish_switch:
                    # bullish switch of the trend
                    signal = -1
                    is_reversal = True
                else:
                    # bearish continuation of the trend
                    signal = 1
            else:
                # previous bullish trend: previous super trend used the lower band
                # bearsish if the latest close is bellow latest lower band
                bearish_switch = close[-1] < latest_lower_band
                if bearish_switch:
                    # bearish switch of the trend
                    signal = 1
                    is_reversal = True
                else:
                    # bullish continuation of the trend
                    signal = -1

        previous_value[self.PREV_ATR] = atr
        previous_value[self.PREV_UPPER_BAND] = latest_upper_band
        previous_value[self.PREV_LOWER_BAND] = latest_lower_band
        # store the latest used super trend band: bullish = lower band, bearish = upper band
        previous_value[self.PREV_SUPERTREND] = latest_lower_band if signal == -1 else latest_upper_band
        self.eval_note = signal if is_reversal or not self.reversals_only else commons_constants.START_PENDING_EVAL_NOTE

    def get_previous_value(self, symbol, time_frame):
        try:
            previous_symbol_value = self.previous_value[symbol]
        except KeyError:
            self.previous_value[symbol] = {}
            previous_symbol_value = self.previous_value[symbol]
        try:
            return previous_symbol_value[time_frame]
        except KeyError:
            previous_symbol_value[time_frame] = {}
            return previous_symbol_value[time_frame]


class DeathAndGoldenCrossEvaluator(evaluators.TAEvaluator):
    FAST_LENGTH = "fast_length"
    SLOW_LENGTH = "slow_length"
    SLOW_MA_TYPE = "slow_ma_type"
    FAST_MA_TYPE = "fast_ma_type"
    MA_TYPES = ["EMA", "WMA", "SMA", "LSMA", "KAMA", "DEMA", "TEMA", "VWMA"]

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.fast_length = 50
        self.slow_length = 200
        self.fast_ma_type = "sma"
        self.slow_ma_type = "sma"
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the evaluator, should define all the evaluator's user inputs
        """
        self.fast_length = self.UI.user_input(self.FAST_LENGTH, enums.UserInputTypes.INT, self.fast_length,
                                              inputs, min_val=1, title="Fast MA length")
        self.slow_length = self.UI.user_input(self.SLOW_LENGTH, enums.UserInputTypes.INT, self.slow_length,
                                              inputs, min_val=1, title="Slow MA length")
        self.fast_ma_type = self.UI.user_input(self.FAST_MA_TYPE, enums.UserInputTypes.OPTIONS, self.fast_ma_type,
                                               inputs, options=self.MA_TYPES, title="Fast MA type").lower()
        self.slow_ma_type = self.UI.user_input(self.SLOW_MA_TYPE, enums.UserInputTypes.OPTIONS, self.slow_ma_type,
                                               inputs, options=self.MA_TYPES, title="Slow MA type").lower()

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):

        close = trading_api.get_symbol_close_candles(self.get_exchange_symbol_data(exchange, exchange_id, symbol),
                                                     time_frame,
                                                     include_in_construction=inc_in_construction_data)
        volume = trading_api.get_symbol_volume_candles(self.get_exchange_symbol_data(exchange, exchange_id, symbol),
                                                       time_frame,
                                                       include_in_construction=inc_in_construction_data)
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        if len(close) > max(self.slow_length, self.fast_length):
            await self.evaluate(cryptocurrency, symbol, time_frame, candle, close, volume)
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))

    async def evaluate(self, cryptocurrency, symbol, time_frame, candle, candle_data, volume_data):
        if self.fast_ma_type == "vwma":
            fast_ma = tulipy.vwma(candle_data, volume_data, self.fast_length)
        elif self.fast_ma_type == "lsma":
            fast_ma = tulipy.linreg(candle_data, self.fast_length)
        else:
            fast_ma = getattr(tulipy, self.fast_ma_type)(candle_data, self.fast_length)

        if self.slow_ma_type == "vwma":
            slow_ma = tulipy.vwma(candle_data, volume_data, self.slow_length)
        elif self.slow_ma_type == "lsma":
            slow_ma = tulipy.linreg(candle_data, self.slow_length)
        else:
            slow_ma = getattr(tulipy, self.slow_ma_type)(candle_data, self.slow_length)

        if min(len(fast_ma), len(slow_ma)) < 2:
            # can't compute crosses: not enough data
            self.logger.debug(f"Not enough data to compute crosses, skipping {symbol} {time_frame} evaluation")
            return

        just_crossed = (
            fast_ma[-1] > slow_ma[-1] and fast_ma[-2] < slow_ma[-2]
        ) or (
            fast_ma[-1] < slow_ma[-1] and fast_ma[-2] > slow_ma[-2]
        )
        if just_crossed:
            # crosses happen when the fast_ma and fast_ma just crossed, therefore when it happened on the last candle
            if fast_ma[-1] > slow_ma[-1]:
                # golden cross
                self.eval_note = -1
            elif fast_ma[-1] < slow_ma[-1]:
                # death cross
                self.eval_note = 1


# evaluates position of the current (2 unit) average trend relatively to the 5 units average and 10 units average trend
class DoubleMovingAverageTrendEvaluator(evaluators.TAEvaluator):

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.slow_period_length = 10
        self.fast_period_length = 5

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the evaluator, should define all the evaluator's user inputs
        """
        self.slow_period_length = self.UI.user_input("long_period_length", enums.UserInputTypes.INT,
                                                     self.slow_period_length,
                                                     inputs, min_val=1, title="Slow SMA length")
        self.fast_period_length = self.UI.user_input("short_period_length", enums.UserInputTypes.INT,
                                                     self.fast_period_length,
                                                     inputs, min_val=1, title="Fast SMA length")

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        candle_data = trading_api.get_symbol_close_candles(self.get_exchange_symbol_data(exchange, exchange_id, symbol),
                                                           time_frame,
                                                           include_in_construction=inc_in_construction_data)
        await self.evaluate(cryptocurrency, symbol, time_frame, candle_data, candle)

    async def evaluate(self, cryptocurrency, symbol, time_frame, candle_data, candle):
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        if len(candle_data) >= max(self.slow_period_length, self.fast_period_length):
            current_moving_average = tulipy.sma(candle_data, 2)
            results = [self.get_moving_average_analysis(candle_data, current_moving_average, time_unit)
                       for time_unit in (self.fast_period_length, self.slow_period_length)]
            if len(results):
                self.eval_note = numpy.mean(results)
            else:
                self.eval_note = commons_constants.START_PENDING_EVAL_NOTE

            if self.eval_note == 0:
                self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))

    # < 0 --> Current average bellow other one (computed using time_period)
    # > 0 --> Current average above other one (computed using time_period)
    @staticmethod
    def get_moving_average_analysis(data, current_moving_average, time_period):

        time_period_unit_moving_average = tulipy.sma(data, time_period)

        # equalize array size
        min_len_arrays = min(len(time_period_unit_moving_average), len(current_moving_average))

        # compute difference between 1 unit values and others ( >0 means currently up the other one)
        values_difference = \
            (current_moving_average[-min_len_arrays:] - time_period_unit_moving_average[-min_len_arrays:])
        values_difference = data_util.drop_nan(values_difference)

        if len(values_difference):
            # indexes where current_unit_moving_average crosses time_period_unit_moving_average
            crossing_indexes = EvaluatorUtil.TrendAnalysis.get_threshold_change_indexes(values_difference, 0)

            multiplier = 1 if values_difference[-1] > 0 else -1

            # check at least some data crossed 0
            if crossing_indexes:
                normalized_data = data_util.normalize_data(values_difference)
                current_value = min(abs(normalized_data[-1]) * 2, 1)
                if math.isnan(current_value):
                    return 0
                # check <= values_difference.count()-1if current value is max/min
                if current_value == 0 or current_value == 1:
                    chances_to_be_max = EvaluatorUtil.TrendAnalysis.get_estimation_of_move_state_relatively_to_previous_moves_length(
                        crossing_indexes,
                        values_difference)
                    return multiplier * current_value * chances_to_be_max
                # other case: maxima already reached => return distance to max
                else:
                    return multiplier * current_value

        # just crossed the average => neutral
        return 0


# evaluates position of the current ema to detect divergences
class EMADivergenceTrendEvaluator(evaluators.TAEvaluator):
    EMA_SIZE = "size"
    SHORT_VALUE = "short"
    LONG_VALUE = "long"

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.period = 50
        self.long_value = 2
        self.short_value = -2

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the evaluator, should define all the evaluator's user inputs
        """
        self.period = self.UI.user_input(self.EMA_SIZE, enums.UserInputTypes.INT, self.period,
                                         inputs, min_val=1, title="EMA period length")
        self.long_value = self.UI.user_input("long_value", enums.UserInputTypes.INT, self.long_value,
                                             inputs, title="Long threshold: Minimum % price difference from EMA "
                                                           "consider a long signal. Should be positive in most cases")
        self.short_value = self.UI.user_input("short_value", enums.UserInputTypes.INT, self.short_value,
                                              inputs, title="Short threshold: Minimum % price difference from EMA "
                                                            "consider a short signal. Should be negative in most cases")

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        candle_data = trading_api.get_symbol_close_candles(self.get_exchange_symbol_data(exchange, exchange_id, symbol),
                                                           time_frame,
                                                           include_in_construction=inc_in_construction_data)
        await self.evaluate(cryptocurrency, symbol, time_frame, candle_data, candle)

    async def evaluate(self, cryptocurrency, symbol, time_frame, candle_data, candle):
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        if len(candle_data) >= self.period:
            current_ema = tulipy.ema(candle_data, self.period)[-1]
            current_price_close = candle_data[-1]
            diff = (current_price_close / current_ema * 100) - 100

            if diff <= self.long_value:
                self.eval_note = -1
            elif diff >= self.short_value:
                self.eval_note = 1
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))
