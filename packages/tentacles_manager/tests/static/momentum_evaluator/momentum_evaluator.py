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

from octobot_evaluators.evaluator import TAEvaluator
from tentacles.Evaluator.Util import TrendAnalysis


class RSIMomentumEvaluator(TAEvaluator):

    def __init__(self):
        super().__init__()
        self.pertinence = 1

    async def ohlcv_callback(self, exchange: str, exchange_id: str, symbol: str, time_frame, candle):
        period_length = 14
        candle_data = self.get_symbol_candles(exchange, exchange_id, symbol, time_frame).\
            get_symbol_close_candles(period_length).base
        if candle_data is not None and len(candle_data) > period_length:
            rsi_v = tulipy.rsi(candle_data, period=period_length)

            if len(rsi_v) and not math.isnan(rsi_v[-1]):
                long_trend = TrendAnalysis.get_trend(rsi_v, self.long_term_averages)
                short_trend = TrendAnalysis.get_trend(rsi_v, self.short_term_averages)

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
                await self.evaluation_completed(self.cryptocurrency, symbol, time_frame)
