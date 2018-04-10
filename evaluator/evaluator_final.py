import logging
import pprint
import threading
from queue import Queue

from config.cst import START_EVAL_NOTE, EvaluatorStates


class FinalEvaluatorThread(threading.Thread):
    def __init__(self, symbol_evaluator):
        super().__init__()
        self.symbol_evaluator = symbol_evaluator
        self.final_eval = START_EVAL_NOTE
        self.state = None
        self.keep_running = True
        self.exchange = None
        self.symbol = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.queue = Queue()

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.logger.debug(" ** NEW STATE ** --> " + str(self.state))
            if self.symbol_evaluator.notifier.enabled():
                self.symbol_evaluator.get_notifier().notify(self.symbol_evaluator.crypto_currency,
                                                            state,
                                                            pprint.pformat(self.symbol_evaluator.get_matrix().get_matrix()))

            elif self.symbol_evaluator.get_trader(self.exchange).enabled():
                self.symbol_evaluator.get_evaluator_creator().create_order(
                    self.symbol,
                    self.exchange,
                    self.symbol_evaluator.get_trader(self.exchange),
                    state)

            elif self.symbol_evaluator.get_trader_simulator(self.exchange).enabled():
                self.symbol_evaluator.get_evaluator_creator().create_order(
                    self.symbol,
                    self.exchange,
                    self.symbol_evaluator.get_trader_simulator(self.exchange),
                    state)

    def get_state(self):
        return self.state

    def get_final_eval(self):
        return self.final_eval

    def prepare(self):
        strategies_analysis_note_counter = 0
        # Strategies analysis
        for evaluated_strategies in self.symbol_evaluator.get_strategies_eval_list():
            self.final_eval += evaluated_strategies.get_eval_note() * evaluated_strategies.get_pertinence()
            strategies_analysis_note_counter += evaluated_strategies.get_pertinence()

        if strategies_analysis_note_counter > 0:
            self.final_eval /= strategies_analysis_note_counter
        else:
            self.final_eval = START_EVAL_NOTE

    def calculate_final(self):
        # TODO : improve
        # self.final_eval = (self.ta_final_eval * EvaluatorsPertinence.TAEvaluator.value
        #                    + self.social_final_eval * EvaluatorsPertinence.SocialEvaluator.value)
        # self.final_eval /= (EvaluatorsPertinence.TAEvaluator.value + EvaluatorsPertinence.SocialEvaluator.value)
        pass

    def create_state(self):
        # TODO : improve
        if self.final_eval < -0.6:
            self.set_state(EvaluatorStates.VERY_LONG)
        elif self.final_eval < -0.2:
            self.set_state(EvaluatorStates.LONG)
        elif self.final_eval < 0.2:
            self.set_state(EvaluatorStates.NEUTRAL)
        elif self.final_eval < 0.6:
            self.set_state(EvaluatorStates.SHORT)
        else:
            self.set_state(EvaluatorStates.VERY_SHORT)

    def finalize(self, exchange, symbol):
        # reset previous note
        self.final_eval = START_EVAL_NOTE
        self.exchange = exchange
        self.symbol = symbol
        self.prepare()
        self.calculate_final()
        self.create_state()
        self.logger.debug("--> " + str(self.state))

    def add_to_queue(self, exchange, symbol):
        self.queue.put(self.finalize(exchange, symbol))

    def run(self):
        while self.keep_running:
            if not self.queue.empty():
                self.queue.get()

    def stop(self):
        self.keep_running = False
