import threading, os
from abc import *

from config.cst import *
from botcore.config.config import load_config


class SocialEvaluator(threading.Thread):
    __metaclass__ = ABCMeta

    def __init__(self):
        threading.Thread.__init__(self)
        self.social_config = None
        self.config = None
        self.logger = None
        self.symbol = None
        self.history_time = None
        self.eval_note = START_EVAL_NOTE
        self.logger = None
        self.pertinence = START_EVAL_PERTINENCE
        self.need_to_notify = False
        self.enabled = True
        self.is_threaded = False
        self.evaluator_threads = []
        self.is_updating = False
        self.load_config()
        self.keep_running = True

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

    @classmethod
    def get_config_file_name(cls):
        return SPECIFIC_CONFIG_PATH + cls.__name__ + CONFIG_FILE_EXT

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

    def get_is_enabled(self):
        return self.enabled

    def get_is_threaded(self):
        return self.is_threaded

    def get_pertinence(self):
        return self.pertinence

    def get_is_updating(self):
        return self.is_updating

    # to implement in subclasses if config necessary
    # required if is_threaded = False --> provide evaluator refreshing time
    def set_default_config(self):
        pass

    def get_social_config(self):
        return self.social_config

    # generic social eval that will call the indicator eval()
    # and provide a safe execution by disabling multi-call
    def eval(self):
        self.is_updating = True
        try:
            self.eval_impl()
        except Exception as e:
            self.logger.error("Exception in eval_impl(): "+str(e))
        finally:
            self.is_updating = False

    # eval new data
    # Notify if new data is relevant
    # example :
    # def eval_impl(self):
    #   for post in post_selected
    #       note = sentiment_evaluator(post.text)
    #       if(note > 10 || note < 0):
    #           self.need_to_notify = True
    #       self.eval_note += note
    @abstractmethod
    def eval_impl(self):
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
