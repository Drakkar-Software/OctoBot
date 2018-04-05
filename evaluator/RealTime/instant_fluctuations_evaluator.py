from evaluator.RealTime.realtime_evaluator import RealTimeEvaluator

from config.cst import *

class InstantFluctuationsEvaluator(RealTimeEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval(self):
        self.is_updating = True
        # check last candle
        self.eval_note = 0.42
        something_is_happening = False
        if something_is_happening:
            self.notify_evaluator_threads(self.__class__.__name__)
        self.is_updating = False

    def set_default_config(self):
        self.specific_config = {
            CONFIG_REFRESH_RATE: 3600
        }

    def run(self):
        while True:
