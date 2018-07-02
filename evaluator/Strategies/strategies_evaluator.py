from abc import *

from config.config import load_config
from config.cst import CONFIG_EVALUATOR_STRATEGIES, STRATEGIES_REQUIRED_TIME_FRAME, CONFIG_FILE_EXT
from evaluator.abstract_evaluator import AbstractEvaluator
from tools.evaluator_divergence_analyser import EvaluatorDivergenceAnalyser
from tools.time_frame_manager import TimeFrameManager


class StrategiesEvaluator(AbstractEvaluator):
    __metaclass__ = AbstractEvaluator

    def __init__(self):
        super().__init__()
        self.matrix = None
        self.divergence_evaluator_analyser = None

    def set_matrix(self, matrix):
        self.matrix = matrix.get_matrix()

    def get_is_evaluable(self):
        return not (self.get_is_updating() or self.matrix is None)

    def create_divergence_analyser(self):
        self.divergence_evaluator_analyser = EvaluatorDivergenceAnalyser()

    def get_divergence(self):
        return self.divergence_evaluator_analyser.update(self.matrix)

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")

    @classmethod
    def get_config_file_name(cls, config_evaluator_type=CONFIG_EVALUATOR_STRATEGIES):
        return super().get_config_file_name(config_evaluator_type)

    @classmethod
    def get_required_time_frames(cls):
        config = cls.get_evaluator_config()
        if STRATEGIES_REQUIRED_TIME_FRAME in config:
            return TimeFrameManager.parse_time_frames(config[STRATEGIES_REQUIRED_TIME_FRAME])
        else:
            raise Exception("'required_time_frames' is missing in {0}{1}".format(cls.get_name(), CONFIG_FILE_EXT))

    @classmethod
    def get_required_evaluators(cls):
        raise NotImplementedError("Get_required_evaluators not implemented")


class MixedStrategiesEvaluator(StrategiesEvaluator):
    __metaclass__ = StrategiesEvaluator

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")
