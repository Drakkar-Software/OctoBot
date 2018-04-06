from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.evaluator_final import FinalEvaluator


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

        self.data_changed = False

        self.creator = EvaluatorCreator(self)

        self.final = FinalEvaluator(self)

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

    def set_history_time(self, history_time):
        self.history_time = history_time

    def get_notifier(self):
        return self.notifier

    def get_trader(self):
        return self.trader

    def get_final(self):
        return self.final

    def get_creator(self):
        return self.creator

    def update_ta_eval(self, ignored_evaluator=None):
        # update only with new data
        if self.data_changed:
            for ta_evaluator in self.creator.get_ta_eval_list():
                ta_evaluator.set_data(self.data)
                if not ta_evaluator.get_name() == ignored_evaluator and ta_evaluator.get_is_evaluable():
                    ta_evaluator.eval()

            # reset data changed after update
            self.data_changed = False

    def update_rules_eval(self, new_matrix, ignored_evaluator=None):
        for rules_evaluator in self.creator.get_rules_eval_list():
            rules_evaluator.set_matrix(new_matrix)
            if not rules_evaluator.get_name() == ignored_evaluator and rules_evaluator.get_is_evaluable():
                rules_evaluator.eval()

    def finalize(self):
        self.final.prepare()
        self.final.calculate_final()
        self.final.create_state()
