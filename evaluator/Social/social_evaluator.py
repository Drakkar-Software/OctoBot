import threading, os
from abc import *

from config.cst import *
from botcore.config.config import load_config

from evaluator.abstract_evaluator import AbstractEvaluator


class SocialEvaluator(AbstractEvaluator, threading.Thread):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        threading.Thread.__init__(self)
        self.social_config = None
        self.need_to_notify = False
        self.is_threaded = False
        self.evaluator_threads = []
        self.load_config()
        self.keep_running = True

    @classmethod
    def get_config_file_name(cls):
        return SPECIFIC_CONFIG_PATH + cls.__name__ + CONFIG_FILE_EXT

    def stop(self):
        self.keep_running = False

    def add_evaluator_thread(self, evaluator_thread):
        self.evaluator_threads.append(evaluator_thread)

    def notify_evaluator_threads(self, notifier_name):
        for thread in self.evaluator_threads:
            thread.notify(notifier_name)

    def load_config(self):
        config_file = self.get_config_file_name()
        if os.path.isfile(config_file):
            self.social_config = load_config(config_file)
        else:
            self.set_default_config()

    def get_is_threaded(self):
        return self.is_threaded

    # to implement in subclasses if config necessary
    # required if is_threaded = False --> provide evaluator refreshing time
    def set_default_config(self):
        pass

    def get_social_config(self):
        return self.social_config

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")

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
        raise NotImplementedError("Eval_impl not implemented")


class StatsSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Eval_impl not implemented")


class ForumSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Eval_impl not implemented")


class NewsSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Eval_impl not implemented")
