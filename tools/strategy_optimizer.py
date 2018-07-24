import logging

from tools.class_inspector import get_class_from_string, evaluator_parent_inspection
from evaluator import Strategies
from evaluator.Strategies.strategies_evaluator import StrategiesEvaluator


class StrategyOptimizer:

    def __init__(self, config, strategy_name):
        self.is_properly_initialized = False
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config
        self.strategy_class = get_class_from_string(strategy_name, StrategiesEvaluator,
                                                    Strategies, evaluator_parent_inspection)
        if not self.strategy_class:
            self.logger.error(f"Impossible to find a strategy matching class name: {strategy_name} in installed "
                              f"strategies. Please make sure to enter the name of the class, "
                              f"ex: FullMixedStrategiesEvaluator")
        else:
            self.is_properly_initialized = True


    def find_optimal_configuration(self):
        return 1



    def print_report(self):
        print(self.strategy_class.get_name())
