import time
from random import randint

from evaluator.Social.social_evaluator import NewsSocialEvaluator


class TwitterNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = True
        self.is_threaded = True

    def get_data(self):
        pass

    def eval(self):
        v = randint(0, 9)
        if v >= 2:
            self.notify_evaluator_threads(self.__class__.__name__)

    def run(self):
        while True:
            self.get_data()
            self.eval()
            time.sleep(2)


class MediumNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False
        self.is_threaded = False

    def get_data(self):
        pass

    def eval(self):
        pass
