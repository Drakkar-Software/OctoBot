import logging
from abc import *
from queue import Queue

from config.cst import INIT_EVAL_NOTE
from tools.asynchronous_server import AsynchronousServer
from tools.notifications import EvaluatorNotification


class AbstractTradingModeDecider(AsynchronousServer):
    __metaclass__ = ABCMeta

    def __init__(self, trading_mode, symbol_evaluator, exchange, symbol):
        super().__init__(self.finalize)
        self.trading_mode = trading_mode
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
        self.VERY_LONG_THRESHOLD = -0.95
        self.LONG_THRESHOLD = -0.25
        self.NEUTRAL_THRESHOLD = 0.25
        self.SHORT_THRESHOLD = 0.95
        self.RISK_THRESHOLD = 0.2

        self.notifier = EvaluatorNotification(self.config)
        self.queue = Queue()

    # create real and/or simulating orders in trader instances
    def create_final_state_orders(self, evaluator_notification):
        # simulated trader
        self._create_order_if_possible(evaluator_notification,
                                       self.symbol_evaluator.get_trader_simulator(self.exchange))

        # real trader
        self._create_order_if_possible(evaluator_notification,
                                       self.symbol_evaluator.get_trader(self.exchange))

    # for each trader call the creator to check if order creation is possible and create it
    def _create_order_if_possible(self, evaluator_notification, trader):
        if trader.is_enabled():
            with trader.get_portfolio() as pf:
                if self.trading_mode.get_creator().can_create_order(self.symbol, self.exchange, self.state, pf):
                    self._push_order_notification_if_possible(
                        self.symbol_evaluator.get_evaluator_order_creator().create_new_order(
                            self.final_eval,
                            self.symbol,
                            self.exchange,
                            trader,
                            pf,
                            self.state),
                        evaluator_notification)

    @staticmethod
    def _push_order_notification_if_possible(order_list, notification):
        if order_list:
            for order in order_list:
                order.get_order_notifier().notify(notification)

    def get_state(self):
        return self.state

    def get_final_eval(self):
        return self.final_eval

    def finalize(self):
        # reset previous note
        self.final_eval = INIT_EVAL_NOTE

        self._set_final_eval()
        self._create_state()

    def stop(self):
        self.keep_running = False

    @abstractmethod
    def _set_final_eval(self):
        raise NotImplementedError("Set_final_eval not implemented")

    @abstractmethod
    def _get_delta_risk(self):
        raise NotImplementedError("Get_delta_risk not implemented")

    @abstractmethod
    def _create_state(self):
        raise NotImplementedError("Create_state not implemented")

    @abstractmethod
    def _set_state(self, new_state):
        raise NotImplementedError("Set_state not implemented")
