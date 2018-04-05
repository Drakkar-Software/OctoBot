import threading
import time

from config.cst import *


class SocialEvaluatorNotThreadedUpdateThread(threading.Thread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.social_evaluator_list = self.parent.evaluator.get_creator().create_social_not_threaded_list()
        self.social_evaluator_list_timers = []
        self.get_eval_timers()

    def get_eval_timers(self):
        for social_eval in self.social_evaluator_list:
            # if key exists --> else this social eval will not be refreshed
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
                self.parent.logger.warn("Social evaluator " + social_eval.__class__.__name__
                                        + " doesn't have a valid social config refresh rate.")

    def run(self):
        while True:
            for social_eval in self.social_evaluator_list_timers:
                now = time.time()
                social_eval["last_refresh"] += now - social_eval["last_refresh_time"]
                social_eval["last_refresh_time"] = now
                if social_eval["last_refresh"] >= social_eval["refresh_rate"]:
                    social_eval["last_refresh"] = 0
                    social_eval["social_evaluator_class_inst"].eval()

            time.sleep(SOCIAL_EVALUATOR_NOT_THREADED_UPDATE_RATE)
