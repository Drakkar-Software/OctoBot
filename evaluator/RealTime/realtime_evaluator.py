import os
import threading
import time
from abc import *

from backtesting.backtesting import Backtesting
from config.config import load_config
from config.cst import *
from evaluator.abstract_evaluator import AbstractEvaluator
from tools.time_frame_manager import TimeFrameManager


class RealTimeEvaluator(AbstractEvaluator, threading.Thread):
    __metaclass__ = AbstractEvaluator

    def __init__(self):
        super().__init__()
        self.specific_config = None
        self.refresh_time = 0
        self.data = None
        self.evaluator_thread_managers = []
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

    def add_evaluator_thread_manager(self, evaluator_thread):
        self.evaluator_thread_managers.append(evaluator_thread)

    def notify_evaluator_thread_managers(self, notifier_name):
        for thread in self.evaluator_thread_managers:
            thread.notify(notifier_name)

    # to implement in subclasses if config necessary
    def set_default_config(self):
        pass

    @abstractmethod
    def _refresh_data(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def _define_refresh_time(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")

    def run(self):
        while self.keep_running:
            now = time.time()
            try:
                self._refresh_data()
            except Exception as e:
                self.logger.error("error when refreshing data for {0}: {1}".format(self.symbol, e))
            self.eval()

            if not Backtesting.enabled(self.config):
                sleeping_time = self.refresh_time - (time.time() - now)
                if sleeping_time > 0:
                    time.sleep(sleeping_time)


class RealTimeTAEvaluator(RealTimeEvaluator):
    __metaclass__ = RealTimeEvaluator

    def __init__(self, exchange_inst, symbol):
        self.exchange = exchange_inst
        super().__init__()
        self.symbol = symbol
        self._define_refresh_time()

    @abstractmethod
    def _refresh_data(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")

    def valid_refresh_time(self, config_refresh_time):
        if config_refresh_time > self.exchange.get_exchange_manager().get_rate_limit() or \
                self.exchange.get_exchange_manager().websocket_available():
            return config_refresh_time
        else:
            return self.exchange.get_exchange_manager().get_rate_limit()

    def _define_refresh_time(self):
        self.refresh_time = self.valid_refresh_time(self.specific_config[CONFIG_REFRESH_RATE])

    def set_default_config(self):
        time_frames = self.exchange.get_exchange_manager().get_config_time_frame()
        min_time_frame = TimeFrameManager.find_min_time_frame(time_frames, MIN_EVAL_TIME_FRAME)
        refresh_rate = DEFAULT_WEBSOCKET_REAL_TIME_EVALUATOR_REFRESH_RATE_SECONDS if \
            self.exchange.get_exchange_manager().websocket_available() \
            else DEFAULT_REST_REAL_TIME_EVALUATOR_REFRESH_RATE_SECONDS

        self.specific_config = {
            CONFIG_TIME_FRAME: min_time_frame,
            CONFIG_REFRESH_RATE: refresh_rate,
        }
