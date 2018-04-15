from config.cst import *
from evaluator.evaluator_dispatcher import *


class AbstractEvaluator:
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.logger = None
        self.config = None
        self.enabled = True
        self.is_updating = False
        self.symbol = None
        self.history_time = None

        self.eval_note = START_PENDING_EVAL_NOTE
        self.pertinence = START_EVAL_PERTINENCE

    @classmethod
    def get_name(cls):
        return cls.__name__

    # Used to provide a new logger for this particular indicator
    def set_logger(self, logger):
        self.logger = logger

    # Used to provide the global config
    def set_config(self, config):
        self.config = config

    # Symbol is the cryptocurrency symbol
    def set_symbol(self, symbol):
        self.symbol = symbol

    # history time represents the period of time of the indicator
    def set_history_time(self, history_time):
        self.history_time = history_time

    # Eval note will be set by the eval_impl at each call
    def get_eval_note(self):
        return self.eval_note

    # Pertinence of indicator will be used with the eval_note to provide a relevancy
    def get_pertinence(self):
        return self.pertinence

    # If this indicator is enabled
    def get_is_enabled(self):
        return self.enabled

    # If the eval method is running
    def get_is_updating(self):
        return self.is_updating

    # generic eval that will call the indicator eval()
    # and provide a safe execution by disabling multi-call
    def eval(self) -> None:
        self.is_updating = True
        try:
            self.eval_impl()
        except Exception as e:
            if CONFIG_DEBUG_OPTION in self.config and self.config[CONFIG_DEBUG_OPTION]:
                raise e
            else:
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

    @classmethod
    def get_is_dispatcher_client(cls):
        return EvaluatorDispatcherClient in cls.__bases__

    def set_eval_note(self, new_eval_note):
        if self.eval_note == START_PENDING_EVAL_NOTE:
            self.eval_note = INIT_EVAL_NOTE

        if self.eval_note + new_eval_note > 1:
            self.eval_note = 1
        elif self.eval_note + new_eval_note < -1:
            self.eval_note = -1
        else:
            self.eval_note += new_eval_note
