from abc import *

from config.cst import *


class AbstractEvaluator:
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.logger = None
        self.config = None
        self.eval_note = START_EVAL_NOTE
        self.pertinence = START_EVAL_PERTINENCE
        self.logger = None
        self.enabled = True
        self.is_updating = False
        self.symbol = None
        self.history_time = None

    @classmethod
    def get_name(cls):
        return cls.__name__

    def set_logger(self, logger):
        self.logger = logger

    def set_config(self, config):
        self.config = config

    def set_symbol(self, symbol):
        self.symbol = symbol

    def set_history_time(self, history_time):
        self.history_time = history_time

    def get_eval_note(self):
        return self.eval_note

    def get_pertinence(self):
        return self.pertinence

    def get_is_enabled(self):
        return self.enabled

    def get_is_updating(self):
        return self.is_updating

    # generic eval that will call the indicator eval()
    # and provide a safe execution by disabling multi-call
    def eval(self) -> None:
        self.is_updating = True
        try:
            self.eval_impl()
        except Exception as e:
            self.logger.error(" Exception in eval_impl(): " + str(e))
        finally:
            self.is_updating = False

    # eval new data
    # Notify if new data is relevant
    # example :
    # def eval_impl(self):
    #   for post in post_selected
    #       note = sentiment_evaluator(post.text)
    #       if(note > 10 || note < 0):
    #           self.need_to_notify = True
    #       self.eval_note += note
    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")