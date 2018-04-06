from abc import *

from config.cst import *


# TODO : temp class
class RulesEvaluator:
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.logger = None
        self.config = None
        self.eval_note = START_EVAL_NOTE
        self.pertinence = START_EVAL_PERTINENCE
        self.logger = None
        self.enabled = True

    @classmethod
    def get_name(cls):
        return cls.__name__

    def set_logger(self, logger):
        self.logger = logger

    def set_config(self, config):
        self.config = config

    def get_eval_note(self):
        return self.eval_note

    def get_pertinence(self):
        return self.pertinence

    def get_is_enabled(self):
        return self.enabled

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")
