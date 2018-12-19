from tools.logging.logging_util import get_logger
import threading
import time

from config import *


class SocialEvaluatorNotThreadedUpdateThread(threading.Thread):

    LAST_REFRESH_KEY = "last_refresh"
    LAST_REFRESH_TIME_KEY = "last_refresh_time"
    REFRESH_RATE_KEY = "refresh_rate"
    EVALUATOR_INSTANCE_KEY = "social_evaluator_class_inst"

    def __init__(self, social_evaluator_list):
        super().__init__()
        self.social_evaluator_list = social_evaluator_list
        self.social_evaluator_list_timers = []
        self.logger = get_logger(self.__class__.__name__)
        self._create_eval_timers()
        self.keep_running = True

    def stop(self):
        self.keep_running = False

    def _create_eval_timers(self):
        for social_eval in self.social_evaluator_list:
            # if key exists --> else this social eval will not be refreshed
            if not social_eval.get_is_self_refreshing():
                if CONFIG_REFRESH_RATE in social_eval.get_social_config():
                    self.social_evaluator_list_timers.append(
                        {
                            self.EVALUATOR_INSTANCE_KEY: social_eval,
                            self.REFRESH_RATE_KEY: social_eval.get_social_config()[CONFIG_REFRESH_RATE],
                            # force first refresh
                            self.LAST_REFRESH_KEY: social_eval.get_social_config()[CONFIG_REFRESH_RATE],
                            self.LAST_REFRESH_TIME_KEY: time.time()
                        })
                else:
                    self.logger.warning(f"Social evaluator {social_eval.get_name()} doesn't have a valid social config "
                                        "refresh rate.")

    def run(self):
        if self.social_evaluator_list_timers:
            while self.keep_running:
                for social_eval in self.social_evaluator_list_timers:
                    now = time.time()
                    social_eval[self.LAST_REFRESH_KEY] += now - social_eval[self.LAST_REFRESH_TIME_KEY]
                    social_eval[self.LAST_REFRESH_TIME_KEY] = now
                    if social_eval[self.LAST_REFRESH_KEY] >= social_eval[self.REFRESH_RATE_KEY]:
                        social_eval[self.LAST_REFRESH_KEY] = 0

                        try:
                            social_eval[self.EVALUATOR_INSTANCE_KEY].get_data()
                            social_eval[self.EVALUATOR_INSTANCE_KEY].eval()
                        except Exception as e:
                            self.logger.error(f"Error during Social not threaded update eval() or get_data() on "
                                              f"{social_eval[self.EVALUATOR_INSTANCE_KEY].get_name()} for "
                                              f"{social_eval[self.EVALUATOR_INSTANCE_KEY].get_symbol()} : {e}")

                time.sleep(SOCIAL_EVALUATOR_NOT_THREADED_UPDATE_RATE)
