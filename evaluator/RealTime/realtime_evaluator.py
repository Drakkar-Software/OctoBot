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
        self.load_config()

    def load_config(self):
        config_file = self.get_config_file_name()
        if os.path.isfile(config_file):
            self.specific_config = load_config(config_file)
        else:
            self.set_default_config()

    def get_config_file_name(self):
        return SPECIFIC_CONFIG_PATH + self.__class__.__name__ + ".json"

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

    def set_data(self, data):
        self.data = data

    # to implement in subclasses if config necessary
    def set_default_config(self):
        pass

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Eval not implemented")
