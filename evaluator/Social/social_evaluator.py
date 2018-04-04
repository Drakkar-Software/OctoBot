import threading
from abc import *

from config.cst import *


class SocialEvaluator(threading.Thread):
    __metaclass__ = ABCMeta

    def __init__(self):
        threading.Thread.__init__(self)
        self.logger = None
        self.symbol = None
        self.history_time = None
        self.config = None
        self.eval_note = START_EVAL_NOTE
        self.logger = None
        self.pertinence = START_EVAL_PERTINENCE
        self.need_to_notify = False
        self.enabled = True

    def set_logger(self, logger):
        self.logger = logger

    def set_symbol(self, symbol):
        self.symbol = symbol

    def set_history_time(self, history_time):
        self.history_time = history_time

    def set_config(self, config):
        self.config = config

    def get_eval_note(self):
        return self.eval_note

    def is_enabled(self):
        return self.enabled

    def get_pertinence(self):
        return self.pertinence

    # getter used be evaluator thread to check if this evaluator notified
    def notify_if_necessary(self):
        current = self.need_to_notify

        # remove notify
        self.need_to_notify = False

        return current

    # eval new data
    # Notify if new data is relevant
    # example :
    # def eval(self):
    #   for post in post_selected
    #       note = sentiment_evaluator(post.text)
    #       if(note > 10 || note < 0):
    #           self.need_to_notify = True
    #       self.eval_note += note
    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")

    # get data needed to perform the eval
    # example :
    # def get_data(self):
    #   for follow in followers:
    #       self.data.append(twitter.API(XXXXX))
    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")

    # thread that will use get_data to provide real time data
    # example :
    # def run(self):
    #     while True:
    #         self.get_data()                           --> pull the new data
    #         self.eval()                               --> create a notification if necessary
    #         time.sleep(own_time * MINUTE_TO_SECONDS)  --> use its own refresh time (near real time)
    @abstractmethod
    def run(self):
        raise NotImplementedError("Eval not implemented")


class StatsSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Eval not implemented")


class ForumSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Eval not implemented")


class NewsSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Eval not implemented")
