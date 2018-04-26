import os
import threading
import time
from abc import *

from config.config import load_config
from config.cst import *
from evaluator.abstract_evaluator import AbstractEvaluator


class RealTimeEvaluator(AbstractEvaluator, threading.Thread):
    __metaclass__ = AbstractEvaluator

    def __init__(self):
        super().__init__()
        self.specific_config = None
        self.data = None
        self.evaluator_threads = []
        self.keep_running = True
        self.load_config()

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

    # to implement in subclasses if config necessary
    def set_default_config(self):
        pass

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Run not implemented")


class RealTimeTAEvaluator(RealTimeEvaluator):
    __metaclass__ = RealTimeEvaluator

    def __init__(self, exchange_inst, symbol):
        super().__init__()
        self.symbol = symbol
        self.exchange = exchange_inst
        self.refresh_time = 0

    @abstractmethod
    def _refresh_data(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")

    def valid_refresh_time(self, config_refresh_time):
        if config_refresh_time > self.exchange.get_rate_limit():
            return config_refresh_time
        else:
            return self.exchange.get_rate_limit()

    def run(self):
        self.refresh_time = self.valid_refresh_time(self.specific_config[CONFIG_REFRESH_RATE])

        while self.keep_running:
            now = time.time()
            self._refresh_data()
            self.eval()
            time.sleep(self.refresh_time - (time.time() - now))
