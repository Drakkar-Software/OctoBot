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


class ScoredRunResult:
    def __init__(self, full_result, optimizer_run_data):
        self.full_result = full_result
        self.optimizer_run_data = optimizer_run_data
        self.values = {}
        self.score = 0
        self.total_weight = 0

    def compute_score(self, relevant_scoring_parameters):
        self.score = 0
        try:
            self.score = sum([
                self._compute_score(scoring_parameter)
                for scoring_parameter in relevant_scoring_parameters
            ]) / self.total_weight
        except ZeroDivisionError:
            self.score = 0

    def _compute_score(self, fitness_parameter):
        try:
            self.values[fitness_parameter.name] = self.full_result[fitness_parameter.name]
            score = fitness_parameter.get_normalized_value(self.values[fitness_parameter.name])
            self.total_weight += fitness_parameter.weight
            return score
        except KeyError:
            return 0

    def __repr__(self):
        return f"[{self.__class__.__name__}] score: {self.score}, total_weight: {self.total_weight}"

    def result_str(self):
        # todo move constants outside of StrategyDesignOptimizer
        import octobot.strategy_optimizer.strategy_design_optimizer as strategy_design_optimizer
        user_inputs = {
            ui[strategy_design_optimizer.StrategyDesignOptimizer.CONFIG_USER_INPUT]:
                ui[strategy_design_optimizer.StrategyDesignOptimizer.CONFIG_VALUE]
            for ui in self.optimizer_run_data
        }
        return f"fitness score: {self.score} {self.values} from {user_inputs}"
