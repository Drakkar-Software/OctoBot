import time
from random import randint

from evaluator.Social.social_evaluator import NewsSocialEvaluator


class TwitterNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = True

    def get_data(self):
        pass

    def eval(self):
        v = randint(0, 9)
        if v == 5:
            self.need_to_notify = True

    def run(self):
        while True:
            self.get_data()
            self.eval()
            time.sleep(2)


class MediumNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def get_data(self):
        pass

    def eval(self):
        pass
