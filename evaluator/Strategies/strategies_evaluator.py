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

from abc import abstractmethod

from config import CONFIG_EVALUATOR_STRATEGIES, STRATEGIES_REQUIRED_TIME_FRAME, STRATEGIES_REQUIRED_EVALUATORS, \
    CONFIG_FORCED_TIME_FRAME, CONFIG_FORCED_EVALUATOR, TENTACLE_DEFAULT_CONFIG, CONFIG_EVALUATORS_WILDCARD
from evaluator.abstract_evaluator import AbstractEvaluator
from tools.evaluator_divergence_analyser import EvaluatorDivergenceAnalyser
from tools.time_frame_manager import TimeFrameManager


class StrategiesEvaluator(AbstractEvaluator):
    __metaclass__ = AbstractEvaluator

    def __init__(self):
        super().__init__()
        self.matrix = None
        self.evaluator_types_matrix = None
        self.divergence_evaluator_analyser = None

    def set_matrix(self, matrix):
        self.matrix = matrix.get_matrix()
        self.evaluator_types_matrix = matrix

    def get_is_evaluable(self):
        return self.matrix is not None

    def create_divergence_analyser(self):
        self.divergence_evaluator_analyser = EvaluatorDivergenceAnalyser()

    def get_divergence(self):
        return self.divergence_evaluator_analyser.update(self.matrix)

    @abstractmethod
    async def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")

    @classmethod
    def get_config_tentacle_type(cls) -> str:
        return CONFIG_EVALUATOR_STRATEGIES

    @classmethod
    def get_required_time_frames(cls, config):
        if CONFIG_FORCED_TIME_FRAME in config:
            return TimeFrameManager.parse_time_frames(config[CONFIG_FORCED_TIME_FRAME])
        strategy_config = cls.get_specific_config()
        if STRATEGIES_REQUIRED_TIME_FRAME in strategy_config:
            return TimeFrameManager.parse_time_frames(strategy_config[STRATEGIES_REQUIRED_TIME_FRAME])
        else:
            raise Exception(f"'{STRATEGIES_REQUIRED_TIME_FRAME}' is missing in {cls.get_config_file_name()}")

    @classmethod
    def get_required_evaluators(cls, config, strategy_config=None):
        if CONFIG_FORCED_EVALUATOR in config:
            return config[CONFIG_FORCED_EVALUATOR]
        strategy_config = strategy_config or cls.get_specific_config()
        if STRATEGIES_REQUIRED_EVALUATORS in strategy_config:
            return strategy_config[STRATEGIES_REQUIRED_EVALUATORS]
        else:
            raise Exception(f"'{STRATEGIES_REQUIRED_EVALUATORS}' is missing in {cls.get_config_file_name()}")

    @classmethod
    def get_default_evaluators(cls, config):
        strategy_config = cls.get_specific_config()
        if TENTACLE_DEFAULT_CONFIG in strategy_config:
            return strategy_config[TENTACLE_DEFAULT_CONFIG]
        else:
            required_evaluators = cls.get_required_evaluators(config, strategy_config)
            if required_evaluators == CONFIG_EVALUATORS_WILDCARD:
                return []
            else:
                return required_evaluators

    # Strategies are not standalone tasks
    async def start_task(self):
        pass


class MixedStrategiesEvaluator(StrategiesEvaluator):
    __metaclass__ = StrategiesEvaluator

    @abstractmethod
    async def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")


class MarketMakingStrategiesEvaluator(StrategiesEvaluator):
    __metaclass__ = StrategiesEvaluator

    @abstractmethod
    async def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")


class StaggeredStrategiesEvaluator(StrategiesEvaluator):
    __metaclass__ = StrategiesEvaluator

    @abstractmethod
    async def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")
