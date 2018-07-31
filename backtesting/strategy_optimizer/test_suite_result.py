import copy

from tools.time_frame_manager import TimeFrameManager
from tools.data_util import DataUtil
from backtesting.strategy_optimizer.strategy_optimizer import StrategyOptimizer


class TestSuiteResult:

    BOT_PROFITABILITY = 0
    MARKET_PROFITABILITY = 1

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
        return StrategyOptimizer.TestSuiteResultSummary(self)

    def get_result_string(self, details=True):
        details = f" details: (profitabilities (bot, market):{self.run_profitabilities}, trades: " \
                  f"{self.trades_counts})" if details else ""
        return (f"{self.get_evaluators_without_strategy()} on {self.time_frames} at risk: {self.risk} "
                f"score: {self.get_average_score():f} (the higher the better) "
                f"average trades: {self.get_average_trades_count():f}{details}")

    class TestSuiteResultSummary:
        def __init__(self, test_suite_result):
            self.evaluators = test_suite_result.get_evaluators_without_strategy()
            self.risk = test_suite_result.risk

        def get_result_string(self):
            return f"{self.evaluators} risk: {self.risk}"

        def __eq__(self, other):
            return self.evaluators == other.evaluators and self.risk == other.risk

        def __hash__(self):
            return abs(hash(f"{self.evaluators}{self.risk}"))
