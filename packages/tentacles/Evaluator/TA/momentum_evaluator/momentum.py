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
import numpy
import tulipy
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.enums as enums
import octobot_commons.data_util as data_util
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.util as evaluators_util
import octobot_trading.api as trading_api
import tentacles.Evaluator.Util as EvaluatorUtil


class RSIMomentumEvaluator(evaluators.TAEvaluator):
    PERIOD_LENGTH = "period_length"
    TREND_CHANGE_IDENTIFIER = "trend_change_identifier"
    LONG_THRESHOLD = "long_threshold"
    SHORT_THRESHOLD = "short_threshold"

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.pertinence = 1
        self.period_length = 14
        self.short_threshold = 70
        self.long_threshold = 30
        self.is_trend_change_identifier = True
        self.short_term_averages = [7, 5, 4, 3, 2, 1]
        self.long_term_averages = [40, 30, 20, 15, 10]

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the evaluator, should define all the evaluator's user inputs
        """
        default_config = self.get_default_config()
        self.period_length = self.UI.user_input(
            self.PERIOD_LENGTH, enums.UserInputTypes.INT, default_config["period_length"],
            inputs, min_val=0, title="RSI period length"
        )

        self.is_trend_change_identifier = self.UI.user_input(
            self.TREND_CHANGE_IDENTIFIER, enums.UserInputTypes.BOOLEAN,
            default_config["trend_change_identifier"], inputs,
            title="Trend identifier: Identify RSI trend changes and evaluate the trend changes strength",
        )
        self.short_threshold = self.UI.user_input(
            self.SHORT_THRESHOLD, enums.UserInputTypes.FLOAT, default_config["short_threshold"], inputs,
            min_val=0,
            title="Short threshold: RSI value from with to send a short (sell) signal. "
                  "Evaluates as 1 when the current RSI value is equal or higher.",
            editor_options={
                enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                  "trend_change_identifier": False
                }
            }
        )
        self.long_threshold = self.UI.user_input(
            self.LONG_THRESHOLD, enums.UserInputTypes.FLOAT, default_config["long_threshold"], inputs,
            min_val=0,
            title="Long threshold: RSI value from with to send a long (buy) signal. "
                  "Evaluates as -1 when the current RSI value is equal or lower.",
            editor_options={
                enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                  "trend_change_identifier": False
                }
            }
        )

    @classmethod
    def get_default_config(
        cls, period_length: typing.Optional[float] = None, trend_change_identifier: typing.Optional[bool] = None,
        short_threshold: typing.Optional[float] = None, long_threshold: typing.Optional[float] = None
    ):
        return {
            cls.PERIOD_LENGTH: period_length or 14,
            cls.TREND_CHANGE_IDENTIFIER: True if trend_change_identifier is None else trend_change_identifier,
            cls.SHORT_THRESHOLD: short_threshold or 70,
            cls.LONG_THRESHOLD: long_threshold or 30,
        }

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        candle_data = trading_api.get_symbol_close_candles(self.get_exchange_symbol_data(exchange, exchange_id, symbol),
                                                           time_frame,
                                                           include_in_construction=inc_in_construction_data)
        await self.evaluate(cryptocurrency, symbol, time_frame, candle_data, candle)

    async def evaluate(self, cryptocurrency, symbol, time_frame, candle_data, candle):
        updated_value = False
        if candle_data is not None and len(candle_data) > self.period_length:
            rsi_v = tulipy.rsi(candle_data, period=self.period_length)
            if len(rsi_v) and not math.isnan(rsi_v[-1]):
                if self.is_trend_change_identifier:
                    long_trend = EvaluatorUtil.TrendAnalysis.get_trend(rsi_v, self.long_term_averages)
                    short_trend = EvaluatorUtil.TrendAnalysis.get_trend(rsi_v, self.short_term_averages)

                    # check if trend change
                    if short_trend > 0 > long_trend:
                        # trend changed to up
                        self.set_eval_note(-short_trend)

                    elif long_trend > 0 > short_trend:
                        # trend changed to down
                        self.set_eval_note(short_trend)

                    # use RSI current value
                    last_rsi_value = rsi_v[-1]
                    if last_rsi_value > 50:
                        self.set_eval_note(rsi_v[-1] / 200)
                    else:
                        self.set_eval_note((rsi_v[-1] - 100) / 200)
                else:
                    self.eval_note = 0
                    if rsi_v[-1] >= self.short_threshold:
                        self.eval_note = 1
                    elif rsi_v[-1] <= self.long_threshold:
                        self.eval_note = -1
                updated_value = True
        if not self.is_trend_change_identifier and not updated_value:
            self.eval_note = 0
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not symbol dependant else False
        """
        return False

    @classmethod
    def get_is_time_frame_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not time_frame dependant else False
        """
        return False


# double RSI analysis
class RSIWeightMomentumEvaluator(evaluators.TAEvaluator):
    PERIOD = "period"
    SLOW_EVAL_COUNT = "slow_eval_count"
    FAST_EVAL_COUNT = "fast_eval_count"
    RSI_TO_WEIGHTS = "RSI_to_weight"
    SLOW_THRESHOLD = "slow_threshold"
    FAST_THRESHOLD = "fast_threshold"
    FAST_THRESHOLDS = "fast_thresholds"
    WEIGHTS = "weights"
    PRICE = "price"
    VOLUME = "volume"

    @staticmethod
    def get_eval_type():
        return typing.Dict[str, int]

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.period_length = 14
        self.slow_eval_count = 16
        self.fast_eval_count = 4
        self.weights = []

    def _init_fast_threshold(self, inputs, indexes, fast_threshold, price_weight, volume_weight):
        self.UI.user_input(self.WEIGHTS, enums.UserInputTypes.OBJECT, None, inputs,
                           parent_input_name=self.FAST_THRESHOLDS,
                           title="Price and volume weights of this interpretation.", array_indexes=indexes)
        return {
            self.FAST_THRESHOLD: self.UI.user_input(self.FAST_THRESHOLD, enums.UserInputTypes.INT, fast_threshold,
                                                    inputs, min_val=0, parent_input_name=self.FAST_THRESHOLDS,
                                                    title="Fast RSI threshold under which this interpretation will "
                                                          "be triggered.", array_indexes=indexes),
            self.WEIGHTS: {
                self.PRICE: self.UI.user_input(self.PRICE, enums.UserInputTypes.OPTIONS, price_weight,
                                               inputs, options=[1, 2, 3], parent_input_name=self.WEIGHTS,
                                               editor_options={"enum_titles": ["Light", "Average", "Heavy"]},
                                               title="Price weight.", array_indexes=indexes),
                self.VOLUME: self.UI.user_input(self.VOLUME, enums.UserInputTypes.OPTIONS, volume_weight,
                                                inputs, options=[1, 2, 3], parent_input_name=self.WEIGHTS,
                                                editor_options={"enum_titles": ["Light", "Average", "Heavy"]},
                                                title="Volume weight.", array_indexes=indexes),
            }
        }

    def _init_RSI_to_weight(self, inputs, slow_threshold, fast_thresholds):
        self.UI.user_input(self.FAST_THRESHOLDS, enums.UserInputTypes.OBJECT_ARRAY, fast_thresholds, inputs,
                           item_title="Fast RSI interpretation",
                           other_schema_values={"minItems": 1, "uniqueItems": True},
                           parent_input_name=self.RSI_TO_WEIGHTS,
                           title="Interpretations on this slow threshold trigger case."),
        return {
            self.SLOW_THRESHOLD: self.UI.user_input(self.SLOW_THRESHOLD, enums.UserInputTypes.INT, slow_threshold,
                                                    inputs,
                                                    min_val=0, parent_input_name=self.RSI_TO_WEIGHTS,
                                                    title="Slow RSI threshold under which this interpretation will "
                                                          "be triggered.", array_indexes=[0]),
            self.FAST_THRESHOLDS: [
                self._init_fast_threshold(inputs, [0, index], *fast_threshold)
                for index, fast_threshold in enumerate(fast_thresholds)
            ],
        }

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.period_length = self.UI.user_input("period", enums.UserInputTypes.INT, self.period_length,
                                                inputs, min_val=1,
                                                title="Period: RSI period length.")
        self.slow_eval_count = self.UI.user_input("slow_eval_count", enums.UserInputTypes.INT, self.slow_eval_count,
                                                  inputs, min_val=1,
                                                  title="Number of recent RSI values to consider to get the current slow "
                                                        "moving market sentiment.")
        self.fast_eval_count = self.UI.user_input("fast_eval_count", enums.UserInputTypes.INT, self.fast_eval_count,
                                                  inputs, min_val=1,
                                                  title="Number of recent RSI values to consider to get the current fast "
                                                        "moving market sentiment.")
        weights = []
        self.weights = sorted(
            self.UI.user_input(self.RSI_TO_WEIGHTS, enums.UserInputTypes.OBJECT_ARRAY, weights, inputs,
                               item_title="Slow RSI interpretation",
                               other_schema_values={"minItems": 1, "uniqueItems": True},
                               title="RSI values and interpretations."),
            key=lambda a: a[self.SLOW_THRESHOLD]
        )
        # init one user input to generate user input schema and default values
        weights.append(self._init_RSI_to_weight(inputs, 30, [[20, 2, 2]]))

        for i, fast_threshold in enumerate(self.weights):
            fast_threshold[self.FAST_THRESHOLDS] = sorted(fast_threshold[self.FAST_THRESHOLDS],
                                                          key=lambda a: a[self.FAST_THRESHOLD])

    def _get_rsi_averages(self, symbol_candles, time_frame, include_in_construction):
        # compute the slow and fast RSI average
        candle_data = trading_api.get_symbol_close_candles(symbol_candles, time_frame,
                                                           include_in_construction=include_in_construction)
        if len(candle_data) > self.period_length:
            rsi_v = tulipy.rsi(candle_data, period=self.period_length)
            rsi_v = data_util.drop_nan(rsi_v)
            if len(rsi_v):
                slow_average = numpy.mean(rsi_v[-self.slow_eval_count:])
                fast_average = numpy.mean(rsi_v[-self.fast_eval_count:])
                return slow_average, fast_average, rsi_v
        return None, None, None

    @staticmethod
    def _check_inferior(bound, val1, val2):
        return val1 < bound and val2 < bound

    def _analyse_dip_weight(self, slow_rsi, fast_rsi, current_rsi):
        # returns price weight, volume weight
        try:
            for slow_rsi_weight in self.weights:
                if slow_rsi < slow_rsi_weight[self.SLOW_THRESHOLD]:
                    for fast_rsi_weight in slow_rsi_weight[self.FAST_THRESHOLDS]:
                        if self._check_inferior(fast_rsi_weight[self.FAST_THRESHOLD], fast_rsi, current_rsi):
                            return fast_rsi_weight[self.WEIGHTS][self.PRICE], \
                                   fast_rsi_weight[self.WEIGHTS][self.VOLUME]
                    # exit loop since the target RSI has been found
                    break
        except KeyError as e:
            self.logger.error(f"Error when reading from config file: missing {e}")
        return None, None

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        try:
            symbol_candles = self.get_exchange_symbol_data(exchange, exchange_id, symbol)
            # compute the slow and fast RSI average
            slow_rsi, fast_rsi, rsi_v = self._get_rsi_averages(symbol_candles, time_frame,
                                                               include_in_construction=inc_in_construction_data)
            current_candle_time = trading_api.get_symbol_time_candles(symbol_candles, time_frame,
                                                                      include_in_construction=inc_in_construction_data)[
                -1]
            await self.evaluate(cryptocurrency, symbol, time_frame, slow_rsi,
                                fast_rsi, rsi_v, current_candle_time, candle)
        except IndexError:
            self.eval_note = commons_constants.START_PENDING_EVAL_NOTE

    async def evaluate(self, cryptocurrency, symbol, time_frame, slow_rsi,
                       fast_rsi, rsi_v, current_candle_time, candle):
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        if slow_rsi is not None and fast_rsi is not None and rsi_v is not None:
            last_rsi_values_to_consider = 5
            analysed_rsi = rsi_v[-last_rsi_values_to_consider:]
            peak_reached = EvaluatorUtil.TrendAnalysis.min_has_just_been_reached(analysed_rsi, acceptance_window=0.95,
                                                                                 delay=2)
            if peak_reached:
                price_weight, volume_weight = self._analyse_dip_weight(slow_rsi, fast_rsi, rsi_v[-1])
                if price_weight is not None and volume_weight is not None:
                    self.eval_note = {
                        "price_weight": price_weight,
                        "volume_weight": volume_weight,
                        "current_candle_time": current_candle_time
                    }
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))


# bollinger_bands
class BBMomentumEvaluator(evaluators.TAEvaluator):

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.period_length = 20

    def init_user_inputs(self, inputs: dict) -> None:
        self.period_length = self.UI.user_input("period_length", enums.UserInputTypes.INT, self.period_length,
                                                inputs, min_val=1,
                                                title="Period: Bollinger bands period length.")

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        candle_data = trading_api.get_symbol_close_candles(self.get_exchange_symbol_data(exchange, exchange_id, symbol),
                                                           time_frame,
                                                           self.period_length,
                                                           include_in_construction=inc_in_construction_data)
        await self.evaluate(cryptocurrency, symbol, time_frame, candle_data, candle)

    async def evaluate(self, cryptocurrency, symbol, time_frame, candle_data, candle):
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        if len(candle_data) >= self.period_length:
            # compute bollinger bands
            lower_band, middle_band, upper_band = tulipy.bbands(candle_data, self.period_length, 2)

            # if close to lower band => low value => bad,
            # therefore if close to middle, value is keeping up => good
            # finally if up the middle one or even close to the upper band => very good

            current_value = candle_data[-1]
            current_up = upper_band[-1]
            current_middle = middle_band[-1]
            current_low = lower_band[-1]
            delta_up = current_up - current_middle
            delta_low = current_middle - current_low

            # its exactly on all bands
            if current_up == current_low:
                self.eval_note = commons_constants.START_PENDING_EVAL_NOTE

            # exactly on the middle
            elif current_value == current_middle:
                self.eval_note = 0

            # up the upper band
            elif current_value > current_up:
                self.eval_note = 1

            # down the lower band
            elif current_value < current_low:
                self.eval_note = -1

            # regular values case: use parabolic factor all the time
            else:

                # up the middle band
                if current_middle < current_value:
                    self.eval_note = math.pow((current_value - current_middle) / delta_up, 2)

                # down the middle band
                elif current_middle > current_value:
                    self.eval_note = -1 * math.pow((current_middle - current_value) / delta_low, 2)
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))


# EMA
class EMAMomentumEvaluator(evaluators.TAEvaluator):
    PERIOD_LENGTH = "period_length"
    PRICE_THRESHOLD_PERCENT = "price_threshold_percent"
    REVERSE_SIGNAL = "reverse_signal"

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.period_length = 21
        self.price_threshold_percent = 2
        self.price_threshold_multiplier = self.price_threshold_percent / 100
        self.reverse_signal = False

    def init_user_inputs(self, inputs: dict) -> None:
        default_config = self.get_default_config()
        self.period_length = self.UI.user_input(
            self.PERIOD_LENGTH, enums.UserInputTypes.INT, default_config["period_length"], inputs,
            min_val=1, title="Period: Moving Average period length."
        )
        self.price_threshold_percent = self.UI.user_input(
            self.PRICE_THRESHOLD_PERCENT, enums.UserInputTypes.FLOAT,
            default_config["price_threshold_percent"], inputs,
            min_val=0,
            title="Price threshold: Percent difference between the current price and current EMA value from "
                  "which to trigger a long or short signal. "
                  "Example with EMA value=200, Price threshold=5: a short signal will fire when price is above or "
                  "equal to 210 and a long signal will when price is bellow or equal to 190",
        )
        self.reverse_signal = self.UI.user_input(
            self.REVERSE_SIGNAL, enums.UserInputTypes.BOOLEAN, default_config["reverse_signal"], inputs,
            title="Reverse signal: when enabled, emits a short signal when the current price is bellow the EMA "
                  "value and long signal when the current price is above the EMA value.",
        )
        self.price_threshold_multiplier = self.price_threshold_percent / 100

    @classmethod
    def get_default_config(
        cls,
        period_length: typing.Optional[int] = None, price_threshold_percent: typing.Optional[float] = None,
        reverse_signal: typing.Optional[bool] = False,
    ) -> dict:
        return {
            cls.PERIOD_LENGTH: period_length or 21,
            cls.PRICE_THRESHOLD_PERCENT: 2 if price_threshold_percent is None else price_threshold_percent,
            cls.REVERSE_SIGNAL: reverse_signal or False,
        }

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        candle_data = trading_api.get_symbol_close_candles(self.get_exchange_symbol_data(exchange, exchange_id, symbol),
                                                           time_frame,
                                                           self.period_length,
                                                           include_in_construction=inc_in_construction_data)
        await self.evaluate(cryptocurrency, symbol, time_frame, candle_data, candle)

    async def evaluate(self, cryptocurrency, symbol, time_frame, candle_data, candle):
        self.eval_note = 0
        if len(candle_data) >= self.period_length:
            # compute ema
            ema_values = tulipy.ema(candle_data, self.period_length)
            is_price_above_ema_threshold = candle_data[-1] >= (ema_values[-1] * (1 + self.price_threshold_multiplier))
            is_price_bellow_ema_threshold = candle_data[-1] <= (ema_values[-1] * (1 - self.price_threshold_multiplier))
            if is_price_above_ema_threshold:
                self.eval_note = 1
            elif is_price_bellow_ema_threshold:
                self.eval_note = -1
            if self.reverse_signal:
                self.eval_note = -1 * self.eval_note
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))


# ADX --> trend_strength
class ADXMomentumEvaluator(evaluators.TAEvaluator):

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.period_length = 14

    def init_user_inputs(self, inputs: dict) -> None:
        self.period_length = self.UI.user_input("period_length", enums.UserInputTypes.INT, self.period_length,
                                                inputs, min_val=1,
                                                title="Period: ADX period length.")

    def _get_minimal_data(self):
        # 26 minimal_data length required for 14 period_length
        return self.period_length + 12

    # implementation according to: https://www.investopedia.com/articles/technical/02/041002.asp => length = 14 and
    # exponential moving average = 20 in a uptrend market
    # idea: adx > 30 => strong trend, < 20 => trend change to come
    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        symbol_candles = self.get_exchange_symbol_data(exchange, exchange_id, symbol)
        close_candles = trading_api.get_symbol_close_candles(symbol_candles, time_frame,
                                                             include_in_construction=inc_in_construction_data)
        if len(close_candles) > self._get_minimal_data():
            high_candles = trading_api.get_symbol_high_candles(symbol_candles, time_frame,
                                                               include_in_construction=inc_in_construction_data)
            low_candles = trading_api.get_symbol_low_candles(symbol_candles, time_frame,
                                                             include_in_construction=inc_in_construction_data)
            await self.evaluate(cryptocurrency, symbol, time_frame, close_candles, high_candles, low_candles, candle)
        else:
            self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
            await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                            eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                    time_frame=time_frame))

    async def evaluate(self, cryptocurrency, symbol, time_frame, close_candles, high_candles, low_candles, candle):
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        if len(close_candles) >= self._get_minimal_data():
            min_adx = 7.5
            max_adx = 45
            neutral_adx = 25
            adx = tulipy.adx(high_candles, low_candles, close_candles, self.period_length)
            instant_ema = data_util.drop_nan(tulipy.ema(close_candles, 2))
            slow_ema = data_util.drop_nan(tulipy.ema(close_candles, 20))
            adx = data_util.drop_nan(adx)

            if len(adx):
                current_adx = adx[-1]
                current_slows_ema = slow_ema[-1]
                current_instant_ema = instant_ema[-1]

                multiplier = -1 if current_instant_ema < current_slows_ema else 1

                # strong adx => strong trend
                if current_adx > neutral_adx:
                    # if max adx already reached => when ADX forms a top and begins to turn down, you should look for a
                    # retracement that causes the price to move toward its 20-day exponential moving average (EMA).
                    adx_last_values = adx[-15:]
                    adx_last_value = adx_last_values[-1]

                    local_max_adx = adx_last_values.max()
                    # max already reached => trend will slow down
                    if adx_last_value < local_max_adx:

                        self.eval_note = multiplier * (current_adx - neutral_adx) / (local_max_adx - neutral_adx)

                    # max not reached => trend will continue, return chances to be max now
                    else:
                        crossing_indexes = EvaluatorUtil.TrendAnalysis.get_threshold_change_indexes(adx, neutral_adx)
                        chances_to_be_max = \
                            EvaluatorUtil.TrendAnalysis.get_estimation_of_move_state_relatively_to_previous_moves_length(
                                crossing_indexes, adx) if len(crossing_indexes) > 2 else 0.75
                        proximity_to_max = min(1, current_adx / max_adx)
                        self.eval_note = multiplier * proximity_to_max * chances_to_be_max

                # weak adx => change to come
                else:
                    self.eval_note = multiplier * min(1, ((neutral_adx - current_adx) / (neutral_adx - min_adx)))
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))


class MACDMomentumEvaluator(evaluators.TAEvaluator):
    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.previous_note = None
        self.long_period_length = 26
        self.short_period_length = 12
        self.signal_period_length = 9

    def init_user_inputs(self, inputs: dict) -> None:
        self.short_period_length = self.UI.user_input(
            "short_period_length", enums.UserInputTypes.INT, self.short_period_length, inputs,
            min_val=1, title="MACD fast period length."
        )
        self.long_period_length = self.UI.user_input(
            "long_period_length", enums.UserInputTypes.INT, self.long_period_length, inputs,
            min_val=1, title="MACD slow period length."
        )
        self.signal_period_length = self.UI.user_input(
            "signal_period_length", enums.UserInputTypes.INT, self.signal_period_length, inputs,
            min_val=1, title="MACD signal period."
        )

    def _analyse_pattern(self, pattern, macd_hist, zero_crossing_indexes, price_weight,
                         pattern_move_time, sign_multiplier):
        # add pattern's strength
        weight = price_weight * EvaluatorUtil.PatternAnalyser.get_pattern_strength(pattern)

        average_pattern_period = 0.7
        if len(zero_crossing_indexes) > 1:
            # compute chances to be after average pattern period
            patterns = [EvaluatorUtil.PatternAnalyser.get_pattern(
                macd_hist[zero_crossing_indexes[i]:zero_crossing_indexes[i + 1]])
                for i in range(len(zero_crossing_indexes) - 1)
            ]
            if 0 != zero_crossing_indexes[0]:
                patterns.append(EvaluatorUtil.PatternAnalyser.get_pattern(macd_hist[0:zero_crossing_indexes[0]]))
            if len(macd_hist) - 1 != zero_crossing_indexes[-1]:
                patterns.append(EvaluatorUtil.PatternAnalyser.get_pattern(macd_hist[zero_crossing_indexes[-1]:]))
            double_patterns_count = patterns.count("W") + patterns.count("M")

            average_pattern_period = EvaluatorUtil.TrendAnalysis. \
                get_estimation_of_move_state_relatively_to_previous_moves_length(
                zero_crossing_indexes,
                macd_hist,
                pattern_move_time,
                double_patterns_count)

        # if we have few data but wave is growing => set higher value
        if len(zero_crossing_indexes) <= 1 and price_weight == 1:
            if self.previous_note is not None:
                average_pattern_period = 0.95
            self.previous_note = sign_multiplier * weight * average_pattern_period
        else:
            self.previous_note = None

        self.eval_note = sign_multiplier * weight * average_pattern_period

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        candle_data = trading_api.get_symbol_close_candles(self.get_exchange_symbol_data(exchange, exchange_id, symbol),
                                                           time_frame,
                                                           include_in_construction=inc_in_construction_data)
        await self.evaluate(cryptocurrency, symbol, time_frame, candle_data, candle)

    async def evaluate(self, cryptocurrency, symbol, time_frame, candle_data, candle):
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        if len(candle_data) > self.long_period_length:
            macd, macd_signal, macd_hist = tulipy.macd(candle_data, self.short_period_length,
                                                       self.long_period_length, self.signal_period_length)

            # on macd hist => M pattern: bearish movement, W pattern: bullish movement
            #                 max on hist: optimal sell or buy
            macd_hist = data_util.drop_nan(macd_hist)
            zero_crossing_indexes = EvaluatorUtil.TrendAnalysis.get_threshold_change_indexes(macd_hist, 0)
            last_index = len(macd_hist) - 1
            pattern, start_index, end_index = EvaluatorUtil.PatternAnalyser.find_pattern(macd_hist,
                                                                                         zero_crossing_indexes,
                                                                                         last_index)

            if pattern != EvaluatorUtil.PatternAnalyser.UNKNOWN_PATTERN:

                # set sign (-1 buy or 1 sell)
                sign_multiplier = -1 if pattern == "W" or pattern == "V" else 1

                # set pattern time frame => W and M are on 2 time frames, others 1
                pattern_move_time = 2 if (pattern == "W" or pattern == "M") and end_index == last_index else 1

                # set weight according to the max value of the pattern and the current value
                current_pattern_start = start_index
                price_weight = macd_hist[-1] / macd_hist[current_pattern_start:].max() if sign_multiplier == 1 \
                    else macd_hist[-1] / macd_hist[current_pattern_start:].min()

                if not math.isnan(price_weight):
                    self._analyse_pattern(pattern, macd_hist, zero_crossing_indexes, price_weight,
                                          pattern_move_time, sign_multiplier)
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))


class KlingerOscillatorMomentumEvaluator(evaluators.TAEvaluator):
    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.short_period = 35  # standard with klinger
        self.long_period = 55  # standard with klinger
        self.ema_signal_period = 13  # standard ema signal for klinger

    def init_user_inputs(self, inputs: dict) -> None:
        self.short_period = self.UI.user_input("short_period", enums.UserInputTypes.INT, self.short_period,
                                               inputs, min_val=1,
                                               title="Short period: length of the short klinger period (standard is 35).")
        self.long_period = self.UI.user_input("long_period", enums.UserInputTypes.INT, self.long_period,
                                              inputs, min_val=1,
                                              title="Long period: length of the long klinger period (standard is 55).")
        self.ema_signal_period = self.UI.user_input("ema_signal_period", enums.UserInputTypes.INT,
                                                    self.ema_signal_period,
                                                    inputs, min_val=1,
                                                    title="Long period: length of the exponential moving average used "
                                                          "to apply on the klinger results (standard is 13).")

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        symbol_candles = self.get_exchange_symbol_data(exchange, exchange_id, symbol)
        high_candles = trading_api.get_symbol_high_candles(symbol_candles, time_frame,
                                                           include_in_construction=inc_in_construction_data)
        if len(high_candles) >= self.short_period:
            low_candles = trading_api.get_symbol_low_candles(symbol_candles, time_frame,
                                                             include_in_construction=inc_in_construction_data)
            close_candles = trading_api.get_symbol_close_candles(symbol_candles, time_frame,
                                                                 include_in_construction=inc_in_construction_data)
            volume_candles = trading_api.get_symbol_volume_candles(symbol_candles, time_frame,
                                                                   include_in_construction=inc_in_construction_data)
            await self.evaluate(cryptocurrency, symbol, time_frame, high_candles, low_candles,
                                close_candles, volume_candles, candle)
        else:
            self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
            await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                            eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                    time_frame=time_frame))

    async def evaluate(self, cryptocurrency, symbol, time_frame, high_candles, low_candles,
                       close_candles, volume_candles, candle):
        eval_proposition = commons_constants.START_PENDING_EVAL_NOTE
        kvo = tulipy.kvo(high_candles,
                         low_candles,
                         close_candles,
                         volume_candles,
                         self.short_period,
                         self.long_period)
        kvo = data_util.drop_nan(kvo)
        if len(kvo) >= self.ema_signal_period:
            kvo_ema = tulipy.ema(kvo, self.ema_signal_period)

            ema_difference = kvo - kvo_ema

            if len(ema_difference) > 1:
                zero_crossing_indexes = EvaluatorUtil.TrendAnalysis.get_threshold_change_indexes(ema_difference, 0)

                current_difference = ema_difference[-1]
                significant_move_threshold = numpy.std(ema_difference)

                factor = 0.2

                if EvaluatorUtil.TrendAnalysis.peak_has_been_reached_already(
                        ema_difference[zero_crossing_indexes[-1]:]):
                    if abs(current_difference) > significant_move_threshold:
                        factor = 1
                    else:
                        factor = 0.5

                eval_proposition = current_difference * factor / significant_move_threshold

                if abs(eval_proposition) > 1:
                    eval_proposition = 1 if eval_proposition > 0 else -1
        self.eval_note = eval_proposition
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))


class KlingerOscillatorReversalConfirmationMomentumEvaluator(evaluators.TAEvaluator):
    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.short_period = 35  # standard with klinger
        self.long_period = 55  # standard with klinger
        self.ema_signal_period = 13  # standard ema signal for klinger

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.short_period = self.UI.user_input("short_period", enums.UserInputTypes.INT, self.short_period,
                                               inputs, min_val=1,
                                               title="Short period: length of the short klinger period (standard is 35).")
        self.long_period = self.UI.user_input("long_period", enums.UserInputTypes.INT, self.long_period,
                                              inputs, min_val=1,
                                              title="Long period: length of the long klinger period (standard is 55).")
        self.ema_signal_period = self.UI.user_input("ema_signal_period", enums.UserInputTypes.INT,
                                                    self.ema_signal_period,
                                                    inputs, min_val=1,
                                                    title="Long period: length of the exponential moving average used "
                                                          "to apply on the klinger results (standard is 13).")

    @staticmethod
    def get_eval_type():
        return bool

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        symbol_candles = self.get_exchange_symbol_data(exchange, exchange_id, symbol)
        high_candles = trading_api.get_symbol_high_candles(symbol_candles, time_frame,
                                                           include_in_construction=inc_in_construction_data)
        if len(high_candles) >= self.short_period:
            low_candles = trading_api.get_symbol_low_candles(symbol_candles, time_frame,
                                                             include_in_construction=inc_in_construction_data)
            close_candles = trading_api.get_symbol_close_candles(symbol_candles, time_frame,
                                                                 include_in_construction=inc_in_construction_data)
            volume_candles = trading_api.get_symbol_volume_candles(symbol_candles, time_frame,
                                                                   include_in_construction=inc_in_construction_data)
            await self.evaluate(cryptocurrency, symbol, time_frame, high_candles, low_candles,
                                close_candles, volume_candles, candle)
        else:
            self.eval_note = False
            await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                            eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                    time_frame=time_frame))

    async def evaluate(self, cryptocurrency, symbol, time_frame, high_candles, low_candles,
                       close_candles, volume_candles, candle):
        if len(high_candles) >= self.short_period:
            kvo = tulipy.kvo(high_candles,
                             low_candles,
                             close_candles,
                             volume_candles,
                             self.short_period,
                             self.long_period)
            kvo = data_util.drop_nan(kvo)
            if len(kvo) >= self.ema_signal_period:

                kvo_ema = tulipy.ema(kvo, self.ema_signal_period)
                ema_difference = kvo - kvo_ema

                if len(ema_difference) > 1:
                    zero_crossing_indexes = EvaluatorUtil.TrendAnalysis.get_threshold_change_indexes(ema_difference, 0)
                    max_elements = 7
                    to_consider_kvo = min(max_elements, len(ema_difference) - zero_crossing_indexes[-1])
                    self.eval_note = EvaluatorUtil.TrendAnalysis.min_has_just_been_reached(
                        ema_difference[-to_consider_kvo:],
                        acceptance_window=0.9, delay=1)
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))
