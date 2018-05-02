import logging
from queue import Queue

from config.cst import EvaluatorStates, INIT_EVAL_NOTE
from evaluator.evaluator_order_creator import EvaluatorOrderCreator
from tools import EvaluatorNotification
from tools.asynchronous_server import AsynchronousServer
from tools.evaluator_divergence_analyser import EvaluatorDivergenceAnalyser


class FinalEvaluator(AsynchronousServer):
    def __init__(self, config, symbol_evaluator, exchange, symbol):
        super().__init__(self.finalize)
        self.symbol_evaluator = symbol_evaluator
        self.config = symbol_evaluator.get_config()
        self.final_eval = INIT_EVAL_NOTE
        self.state = None
        self.keep_running = True
        self.exchange = exchange
        self.symbol = symbol
        self.is_computing = False
        self.logger = logging.getLogger(self.__class__.__name__)

        # If final_eval not is < X_THRESHOLD --> state = X
        self.VERY_LONG_THRESHOLD = -0.75
        self.LONG_THRESHOLD = -0.25
        self.NEUTRAL_THRESHOLD = 0.25
        self.SHORT_THRESHOLD = 0.75
        self.RISK_THRESHOLD = 0.2

        if EvaluatorDivergenceAnalyser.enabled(config):
            self.divergence_evaluator_analyser = EvaluatorDivergenceAnalyser()
        else:
            self.divergence_evaluator_analyser = None

        self.notifier = EvaluatorNotification(self.config)
        self.queue = Queue()

    def _set_state(self, state):
        if state != self.state:
            self.state = state
            self.logger.info(" ** NEW FINAL STATE ** : {0}".format(self.state))

            # cancel open orders
            if self.symbol_evaluator.get_trader(self.exchange).enabled():
                self.symbol_evaluator.get_trader(self.exchange).cancel_open_orders(self.symbol)
            if self.symbol_evaluator.get_trader_simulator(self.exchange).enabled():
                self.symbol_evaluator.get_trader_simulator(self.exchange).cancel_open_orders(self.symbol)

            # create notification
            evaluator_notification = None
            if self.notifier.enabled() and self.state is not EvaluatorStates.NEUTRAL:
                evaluator_notification = self.notifier.notify_state_changed(
                    self.final_eval,
                    self.symbol_evaluator,
                    self.symbol_evaluator.get_trader(self.exchange),
                    self.state,
                    self.symbol_evaluator.get_matrix(self.exchange).get_matrix())

            # call orders creation method
            self.create_final_state_orders(evaluator_notification)

    # create real and/or simulating orders in trader instances
    def create_final_state_orders(self, evaluator_notification):
        # create orders
        if EvaluatorOrderCreator.can_create_order(self.symbol,
                                                  self.exchange,
                                                  self.symbol_evaluator.get_trader(
                                                      self.exchange),
                                                  self.state):

            # create real exchange order
            if self.symbol_evaluator.get_trader(self.exchange).enabled():
                FinalEvaluator._push_order_notification_if_possible(
                    self.symbol_evaluator.get_evaluator_order_creator().create_new_order(
                        self.final_eval,
                        self.symbol,
                        self.exchange,
                        self.symbol_evaluator.get_trader(self.exchange),
                        self.state),
                    evaluator_notification)

            # create trader simulator order
            if self.symbol_evaluator.get_trader_simulator(self.exchange).enabled():
                FinalEvaluator._push_order_notification_if_possible(
                    self.symbol_evaluator.get_evaluator_order_creator().create_new_order(
                        self.final_eval,
                        self.symbol,
                        self.exchange,
                        self.symbol_evaluator.get_trader_simulator(self.exchange),
                        self.state),
                    evaluator_notification)

    @staticmethod
    def _push_order_notification_if_possible(order, notification):
        if order is not None:
            order.get_order_notifier().notify(notification)

    def get_state(self):
        return self.state

    def get_final_eval(self):
        return self.final_eval

    def _prepare(self):
        strategies_analysis_note_counter = 0
        # Strategies analysis
        for evaluated_strategies in self.symbol_evaluator.get_strategies_eval_list(self.exchange):
            self.final_eval += evaluated_strategies.get_eval_note() * evaluated_strategies.get_pertinence()
            strategies_analysis_note_counter += evaluated_strategies.get_pertinence()

        if strategies_analysis_note_counter > 0:
            self.final_eval /= strategies_analysis_note_counter
        else:
            self.final_eval = INIT_EVAL_NOTE

    def _create_state(self):
        risk = self.symbol_evaluator.get_trader(self.exchange).get_risk()

        if self.final_eval < self.VERY_LONG_THRESHOLD - (self.RISK_THRESHOLD * risk):
            self._set_state(EvaluatorStates.VERY_LONG)

        elif self.final_eval < self.LONG_THRESHOLD + (self.RISK_THRESHOLD * risk):
            self._set_state(EvaluatorStates.LONG)

        elif self.final_eval < self.NEUTRAL_THRESHOLD - (self.RISK_THRESHOLD * risk):
            self._set_state(EvaluatorStates.NEUTRAL)

        elif self.final_eval < self.SHORT_THRESHOLD + (self.RISK_THRESHOLD * risk):
            self._set_state(EvaluatorStates.SHORT)

        else:
            self._set_state(EvaluatorStates.VERY_SHORT)

    def finalize(self):
        # reset previous note
        self.final_eval = INIT_EVAL_NOTE

        # check eval notes divergence
        if self.divergence_evaluator_analyser is not None:
            self.divergence_evaluator_analyser.notify_matrix_update(self.symbol_evaluator.get_matrix(self.exchange).get_matrix())

        self._prepare()
        self._create_state()

    def stop(self):
        self.keep_running = False
