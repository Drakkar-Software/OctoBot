import threading, os

from abc import *

from config.cst import *
from botcore.config.config import load_config


class RealTimeEvaluator(threading.Thread):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.specific_config = None
        self.logger = None
        self.config = None
        self.eval_note = START_EVAL_NOTE
        self.pertinence = START_EVAL_PERTINENCE
        self.logger = None
        self.data = None
        self.enabled = True
        self.is_updating = False
        self.evaluator_threads = []
        self.keep_running = True
        self.load_config()

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def get_config_file_name(cls):
        return SPECIFIC_CONFIG_PATH + cls.get_name() + ".json"

    def stop(self):
        self.keep_running = False

    def load_config(self):
        config_file = self.get_config_file_name()
        if os.path.isfile(config_file):
            self.specific_config = load_config(config_file)
        else:
            self.set_default_config()

    def add_evaluator_thread(self, evaluator_thread):
        self.evaluator_threads.append(evaluator_thread)

    def notify_evaluator_threads(self, notifier_name):
        for thread in self.evaluator_threads:
            thread.notify(notifier_name)

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

    # to implement in subclasses if config necessary
    def set_default_config(self):
        pass

    def eval(self):
        self.is_updating = True
        try:
            self.eval_impl()
        except Exception as e:
            self.logger.error(" Exception in eval_impl(): "+str(e))
        finally:
            self.is_updating = False

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Eval_impl not implemented")


class RealTimeTAEvaluator(RealTimeEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self, exchange_inst, symbol):
        super().__init__()
        self.symbol = symbol
        self.exchange = exchange_inst
        self.exchange_time_frame = self.exchange.get_time_frame_enum()

    @abstractmethod
    def refresh_data(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Eval_impl not implemented")