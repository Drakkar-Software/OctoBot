import logging
import threading
import time

from config.cst import *


class SocialEvaluatorNotThreadedUpdateThread(threading.Thread):
    def __init__(self, social_evaluator_list):
        super().__init__()
        self.social_evaluator_list = social_evaluator_list
        self.social_evaluator_list_timers = []
        self.logger = logging.getLogger(self.__class__.__name__)
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
                            "social_evaluator_class_inst": social_eval,
                            "refresh_rate": social_eval.get_social_config()[CONFIG_REFRESH_RATE],
                            # force first refresh
                            "last_refresh": social_eval.get_social_config()[CONFIG_REFRESH_RATE],
                            "last_refresh_time": time.time()
                        })
                else:
                    self.logger.warning("Social evaluator {0} doesn't have a valid social config refresh rate."
                                        .format(social_eval.__class__.__name__))

    def run(self):
        if self.social_evaluator_list_timers:
            while self.keep_running:
                for social_eval in self.social_evaluator_list_timers:
                    now = time.time()
                    social_eval["last_refresh"] += now - social_eval["last_refresh_time"]
                    social_eval["last_refresh_time"] = now
                    if social_eval["last_refresh"] >= social_eval["refresh_rate"]:
                        social_eval["last_refresh"] = 0
                        social_eval["social_evaluator_class_inst"].get_data()
                        social_eval["social_evaluator_class_inst"].eval()

                time.sleep(SOCIAL_EVALUATOR_NOT_THREADED_UPDATE_RATE)
