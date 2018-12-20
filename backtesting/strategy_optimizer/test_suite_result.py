#  Drakkar-Software OctoBot
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

import copy

from tools.time_frame_manager import TimeFrameManager
from tools.data_util import DataUtil


class TestSuiteResult:

    BOT_PROFITABILITY = 0
    MARKET_PROFITABILITY = 1

    INDEX = "id"
    EVALUATORS = "evaluators"
    TIME_FRAMES = "time_frames"
    RISK = "risk"
    SCORE = "score"
    AVERAGE_TRADES = "average_trades"

    def __init__(self, run_profitabilities, trades_counts, risk, time_frames, evaluators, strategy):
        self.run_profitabilities = run_profitabilities
        self.trades_counts = trades_counts
        self.risk = risk
        self.time_frames = time_frames
        self.min_time_frame = TimeFrameManager.find_min_time_frame(self.time_frames)
        self.evaluators = evaluators
        self.strategy = strategy

    def get_average_score(self):
        bot_profitabilities = [
            profitability_result[self.BOT_PROFITABILITY] - profitability_result[self.MARKET_PROFITABILITY]
            for profitability_result in self.run_profitabilities]
        return DataUtil.mean(bot_profitabilities)

    def get_average_trades_count(self):
        return DataUtil.mean(self.trades_counts)

    def get_evaluators_without_strategy(self):
        evals = copy.copy(self.evaluators)
        evals.pop(self.strategy)
        return [eval_name for eval_name in evals]

    def get_config_summary(self):
        return TestSuiteResultSummary(self)

    def get_result_string(self, details=True):
        details = f" details: (profitabilities (bot, market):{self.run_profitabilities}, trades: " \
                  f"{self.trades_counts})" if details else ""
        return (f"{self.get_evaluators_without_strategy()} on {self.time_frames} at risk: {self.risk} "
                f"score: {self.get_average_score():f} (the higher the better) "
                f"average trades: {self.get_average_trades_count():f}{details}")

    def get_result_dict(self, index=0):
        return self.convert_result_into_dict(index, self.get_evaluators_without_strategy(), self.time_frames,
                                             self.risk, round(self.get_average_score(), 5),
                                             round(self.get_average_trades_count(), 5))

    @staticmethod
    def convert_result_into_dict(index, evaluators, time_frames, risk, score, trades):
        return {
            TestSuiteResult.INDEX: index,
            TestSuiteResult.EVALUATORS: evaluators,
            TestSuiteResult.TIME_FRAMES: time_frames,
            TestSuiteResult.RISK: risk,
            TestSuiteResult.SCORE: score,
            TestSuiteResult.AVERAGE_TRADES: trades,
        }


class TestSuiteResultSummary:
    def __init__(self, test_suite_result):
        self.evaluators = test_suite_result.get_evaluators_without_strategy()
        self.risk = test_suite_result.risk

    def get_evaluators(self):
        return self.evaluators

    def get_risk(self):
        return self.risk

    def get_result_string(self):
        return f"{self.evaluators} risk: {self.risk}"

    def __eq__(self, other):
        return self.evaluators == other.evaluators and self.risk == other.risk

    def __hash__(self):
        return abs(hash(f"{self.evaluators}{self.risk}"))
