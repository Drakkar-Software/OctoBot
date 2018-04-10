from evaluator.evaluator_creator import EvaluatorCreator


class Evaluator:
    def __init__(self):
        self.config = None
        self.symbol = None
        self.time_frame = None
        self.history_time = None
        self.data = None
        self.symbol = None
        self.exchange = None
        self.symbol_evaluator = None
        self.data_changed = False

        self.creator = EvaluatorCreator(self)

    def set_config(self, config):
        self.config = config

    def set_data(self, data):
        self.data = data
        self.data_changed = True

    def set_symbol(self, symbol):
        self.symbol = symbol

    def set_time_frame(self, time_frame):
        self.time_frame = time_frame
        self.history_time = time_frame.value

    def set_history_time(self, history_time):
        self.history_time = history_time

    def set_exchange(self, exchange):
        self.exchange = exchange

    def set_symbol_evaluator(self, symbol_evaluator):
        self.symbol_evaluator = symbol_evaluator

    def update_ta_eval(self, ignored_evaluator=None):
        # update only with new data
        if self.data_changed:
            for ta_evaluator in self.creator.get_ta_eval_list():
                ta_evaluator.set_data(self.data)
                if not ta_evaluator.get_name() == ignored_evaluator and ta_evaluator.get_is_evaluable():
                    ta_evaluator.eval()

            # reset data changed after update
            self.data_changed = False

    def get_data(self):
        return self.data

    def get_symbol_evaluator(self):
        return self.symbol_evaluator

    def get_exchange(self):
        return self.exchange

    def get_symbol(self):
        return self.symbol

    def get_creator(self):
        return self.creator
