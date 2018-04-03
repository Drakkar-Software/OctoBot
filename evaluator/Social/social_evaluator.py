import threading
import time

from abc import *
from config.cst import *


class SocialEvaluator(threading.Thread):
    __metaclass__ = ABCMeta

    def __init__(self, evaluation_matrix, TA_threads):
        threading.Thread.__init__(self)
        self.logger = None
        self.symbol = None
        self.history_time = None
        self.config = None
        self.eval_note = START_EVAL_NOTE
        self.logger = None
        self.pertinence = START_EVAL_PERTINENCE
        self._evaluationMatrix = evaluation_matrix  #used only for debug purposes
        self.evaluator_threads = TA_threads
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

    def get_pertinence(self):
        return self.pertinence

    def is_enabled(self):
        return self.enabled

    def get_evaluator_name(self):
        return self.__class__.__name__

    def notify_if_necessary(self):
        if self.need_to_notify():
            self.notify_evaluator_threads()
            print("notified with value: "+str(self.eval_note))

    def notify_evaluator_threads(self):
        for thread in self.evaluator_threads:
            thread.notify(self.get_evaluator_name())

    # updates local matrix and all TA threads matrix
    def update_evaluation_matrix(self):
        self._evaluationMatrix.set_social_eval(self.get_evaluator_name(), self.get_eval_note())
        for thread in self.evaluator_threads:
            thread.get_evaluation_matrix().set_social_eval(self.get_evaluator_name(), self.get_eval_note())

    @abstractmethod
    def need_to_notify(self):
        raise NotImplementedError("NeedToNotify not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Run not implemented")

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")


class StatsSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self, evaluation_matrix, evaluator_thread):
        super().__init__(evaluation_matrix, evaluator_thread)
        self.updatePeriod = 10; #default update period, to specify later in config according to evaluator

    def run(self):
        while True:
            self.get_data()
            self.eval()
            self.update_evaluation_matrix()
            self.notify_if_necessary()
            time.sleep(2)

    @abstractmethod
    def need_to_notify(self):
        raise NotImplementedError("NeedToNotify not implemented")

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")


class ForumSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self, evaluation_matrix, evaluator_thread):
        super().__init__(evaluation_matrix, evaluator_thread)

    # To define here or in impletementation according to available APIs
    @abstractmethod
    def run(self):
        raise NotImplementedError("Run not implemented")

    @abstractmethod
    def need_to_notify(self):
        raise NotImplementedError("NeedToNotify not implemented")

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")


class NewsSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self, evaluation_matrix, evaluator_thread):
        super().__init__(evaluation_matrix, evaluator_thread)

    # To define here or in impletementation according to available APIs
    @abstractmethod
    def run(self):
        raise NotImplementedError("Run not implemented")

    @abstractmethod
    def need_to_notify(self):
        raise NotImplementedError("NeedToNotify not implemented")

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")
