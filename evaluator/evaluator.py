import logging

from evaluator.Social import *
from evaluator.TA import *
from exchanges.trader import *


class Evaluator:
    def __init__(self):
        self.config = None
        self.symbol = None
        self.time_frame = None
        self.history_time = None
        self.data = None
        self.symbol = None
        self.notifier = None
        self.trader = None

        # events
        self.data_changed = False

        self.social_eval_list = []
        self.ta_eval_list = []
        self.ta_eval_not_threaded_list = []

        self.final_eval = START_EVAL_NOTE
        self.social_final_eval = START_EVAL_NOTE
        self.ta_final_eval = START_EVAL_NOTE
        self.state = EvaluatorStates.NEUTRAL

    def set_config(self, config):
        self.config = config

    def set_data(self, data):
        self.data = data
        self.data_changed = True

    def set_notifier(self, notifier):
        self.notifier = notifier

    def set_trader(self, trader):
        self.trader = trader

    def set_symbol(self, symbol):
        self.symbol = symbol

    def set_time_frame(self, time_frame):
        self.time_frame = time_frame
        self.history_time = time_frame.value

    def set_state(self, state):
        if state != self.state:
            self.state = state
            if self.notifier.enabled():
                self.notifier.notify(self.time_frame, self.symbol, state)
            else:
                # TODO : prepare trade
                self.trader.create_order(TraderOrderType.BUY_LIMIT)

    def get_state(self):
        return self.state

    def set_history_time(self, history_time):
        self.history_time = history_time

    def get_final_eval(self):
        return self.final_eval

    def get_social_eval_list(self):
        return self.social_eval_list

    def get_ta_eval_list(self):
        return self.ta_eval_list

    def set_social_eval(self, new_social_list, evaluator_thread):
        self.social_eval_list = new_social_list
        for social_eval in self.social_eval_list:
            social_eval.add_evaluator_thread(evaluator_thread)

    @staticmethod
    def create_social_eval(config, symbol):
        social_eval_list = []
        for social_type in SocialEvaluator.__subclasses__():
            for social_eval_class_type in social_type.__subclasses__():
                social_eval_class = social_eval_class_type()
                if social_eval_class.get_is_enabled():
                    social_eval_class.set_logger(logging.getLogger(social_eval_class_type.__name__))
                    social_eval_class.set_config(config)
                    social_eval_class.set_symbol(symbol)

                    # start refreshing thread
                    if social_eval_class.get_is_threaded():
                        social_eval_class.start()

                    social_eval_list.append(social_eval_class)

        return social_eval_list

    def create_social_not_threaded_list(self):
        for social_eval in self.social_eval_list:

            # if not threaded --> ask him to refresh with generic thread
            if not social_eval.get_is_threaded():
                self.ta_eval_not_threaded_list.append(social_eval)

        return self.ta_eval_not_threaded_list

    def create_ta_eval(self):
        if not self.ta_eval_list:
            for ta_type in TAEvaluator.__subclasses__():
                for ta_eval_class_type in ta_type.__subclasses__():
                    ta_eval_class = ta_eval_class_type()
                    if ta_eval_class.get_is_enabled():
                        ta_eval_class.set_logger(logging.getLogger(ta_eval_class_type.__name__))
                        ta_eval_class.set_config(self.config)
                        ta_eval_class.set_data(self.data)

                        self.ta_eval_list.append(ta_eval_class)

        return self.ta_eval_list

    def update_ta_eval(self, ignored_evaluator=None):
        # update only with new data
        if self.data_changed:
            for ta_evaluator in self.ta_eval_list:
                ta_evaluator.set_data(self.data)
                if not ta_evaluator.__class__.__name__ == ignored_evaluator and ta_evaluator.get_is_evaluable():
                    ta_evaluator.eval()

            # reset data changed after update
            self.data_changed = False

    def finalize(self):
        ta_analysis_note_counter = 0
        # TA analysis
        for evaluated in self.ta_eval_list:
            self.ta_final_eval += evaluated.get_eval_note() * evaluated.get_pertinence()
            ta_analysis_note_counter += evaluated.get_pertinence()

        if ta_analysis_note_counter > 0:
            self.ta_final_eval /= ta_analysis_note_counter
        else:
            self.ta_final_eval = START_EVAL_NOTE

        # Social analysis
        social_analysis_note_counter = 0
        for evaluated in self.social_eval_list:
            self.social_final_eval += evaluated.get_eval_note() * evaluated.get_pertinence()
            social_analysis_note_counter += evaluated.get_pertinence()

        if social_analysis_note_counter > 0:
            self.social_final_eval /= social_analysis_note_counter
        else:
            self.social_final_eval = START_EVAL_NOTE

        # TODO : improve
        self.final_eval = (self.ta_final_eval * EvaluatorsPertinence.TAEvaluator.value
                           + self.social_final_eval * EvaluatorsPertinence.SocialEvaluator.value)
        self.final_eval /= (EvaluatorsPertinence.TAEvaluator.value + EvaluatorsPertinence.SocialEvaluator.value)

        # TODO : improve
        if self.final_eval < 0.2:
            self.set_state(EvaluatorStates.VERY_LONG)
        elif self.final_eval < 0.4:
            self.set_state(EvaluatorStates.LONG)
        elif self.final_eval < 0.6:
            self.set_state(EvaluatorStates.NEUTRAL)
        elif self.final_eval < 0.8:
            self.set_state(EvaluatorStates.SHORT)
        else:
            self.set_state(EvaluatorStates.VERY_SHORT)
