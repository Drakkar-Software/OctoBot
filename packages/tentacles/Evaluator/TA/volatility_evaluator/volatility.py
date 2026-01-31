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
import tulipy

import octobot_commons.constants as commons_constants
import octobot_commons.enums as enums
import octobot_commons.data_util as data_util
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.util as evaluators_util
import octobot_trading.api as trading_api


class StochasticRSIVolatilityEvaluator(evaluators.TAEvaluator):
    STOCHRSI_PERIOD = "period"
    HIGH_LEVEL = "high_level"
    LOW_LEVEL = "low_level"
    TULIPY_INDICATOR_MULTIPLICATOR = 100

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.period = 14
        self.low_level = 1
        self.high_level = 98

    def init_user_inputs(self, inputs: dict) -> None:
        self.period = self.UI.user_input(self.STOCHRSI_PERIOD, enums.UserInputTypes.INT,
                                         self.period, inputs, min_val=2,
                                         title="Period: length of the stochastic RSI period.")
        self.low_level = self.UI.user_input(self.LOW_LEVEL, enums.UserInputTypes.FLOAT,
                                            self.low_level, inputs, min_val=0,
                                            title="Low threshold: stochastic RSI level from which evaluation "
                                                  "is considered a buy signal.")
        self.high_level = self.UI.user_input(self.HIGH_LEVEL, enums.UserInputTypes.FLOAT,
                                             self.high_level, inputs, min_val=0,
                                             title="High threshold: stochastic RSI level from which evaluation "
                                                   "is considered a sell signal.")

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        candle_data = trading_api.get_symbol_close_candles(self.get_exchange_symbol_data(exchange, exchange_id, symbol),
                                                           time_frame,
                                                           include_in_construction=inc_in_construction_data)
        await self.evaluate(cryptocurrency, symbol, time_frame, candle_data, candle)

    async def evaluate(self, cryptocurrency, symbol, time_frame, candle_data, candle):
        try:
            if len(candle_data) >= self.period * 2:
                stochrsi_value = tulipy.stochrsi(data_util.drop_nan(candle_data), self.period)[-1]

                if stochrsi_value * self.TULIPY_INDICATOR_MULTIPLICATOR >= self.high_level:
                    self.eval_note = 1
                elif stochrsi_value * self.TULIPY_INDICATOR_MULTIPLICATOR <= self.low_level:
                    self.eval_note = -1
                else:
                    self.eval_note = stochrsi_value - 0.5
        except tulipy.lib.InvalidOptionError as e:
            message = ""
            if self.period <= 1:
                message = " period should be higher than 1."
            self.logger.warning(f"Error when computing StochasticRSIVolatilityEvaluator: {e}{message}")
            self.logger.exception(e, False)
            self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                        eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                time_frame=time_frame))
