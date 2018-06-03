from config.cst import EvaluatorStates, INIT_EVAL_NOTE
from tools.evaluators_util import check_valid_eval_note
from trading.trader.modes.abstract_mode_creator import AbstractTradingModeCreator
from trading.trader.modes.abstract_mode_decider import AbstractTradingModeDecider
from trading.trader.modes.abstract_trading_mode import AbstractTradingMode


class DailyTradingMode(AbstractTradingMode):
    def __init__(self, config, symbol_evaluator, exchange, symbol):
        super().__init__(config)

        self.set_creator(DailyTradingModeCreator(self))
        self.set_decider(DailyTradingModeDecider(self, symbol_evaluator, exchange, symbol))


class DailyTradingModeCreator(AbstractTradingModeCreator):
    def __init__(self, trading_mode):
        super().__init__(trading_mode)


class DailyTradingModeDecider(AbstractTradingModeDecider):
    def __init__(self, trading_mode, symbol_evaluator, exchange, symbol):
        super().__init__(trading_mode, symbol_evaluator, exchange, symbol)

    def _set_final_eval(self):
        strategies_analysis_note_counter = 0
        # Strategies analysis
        for evaluated_strategies in self.symbol_evaluator.get_strategies_eval_list(self.exchange):
            strategy_eval = evaluated_strategies.get_eval_note()
            if check_valid_eval_note(strategy_eval):
                self.final_eval += strategy_eval * evaluated_strategies.get_pertinence()
                strategies_analysis_note_counter += evaluated_strategies.get_pertinence()

        if strategies_analysis_note_counter > 0:
            self.final_eval /= strategies_analysis_note_counter
        else:
            self.final_eval = INIT_EVAL_NOTE

    def _get_delta_risk(self):
        return self.RISK_THRESHOLD * self.symbol_evaluator.get_trader(self.exchange).get_risk()

    def _create_state(self):
        delta_risk = self._get_delta_risk()

        if self.final_eval < self.VERY_LONG_THRESHOLD + delta_risk:
            self._set_state(EvaluatorStates.VERY_LONG)

        elif self.final_eval < self.LONG_THRESHOLD + delta_risk:
            self._set_state(EvaluatorStates.LONG)

        elif self.final_eval < self.NEUTRAL_THRESHOLD - delta_risk:
            self._set_state(EvaluatorStates.NEUTRAL)

        elif self.final_eval < self.SHORT_THRESHOLD - delta_risk:
            self._set_state(EvaluatorStates.SHORT)

        else:
            self._set_state(EvaluatorStates.VERY_SHORT)

    def _set_state(self, new_state):
        if new_state != self.state:
            # previous_state = self.state
            self.state = new_state
            self.logger.info("{0} ** NEW FINAL STATE ** : {1}".format(self.symbol, self.state))

            # if new state is not neutral --> cancel orders and create new else keep orders
            if new_state is not EvaluatorStates.NEUTRAL:

                # cancel open orders
                if self.symbol_evaluator.get_trader(self.exchange).is_enabled():
                    self.symbol_evaluator.get_trader(self.exchange).cancel_open_orders(self.symbol)
                if self.symbol_evaluator.get_trader_simulator(self.exchange).is_enabled():
                    self.symbol_evaluator.get_trader_simulator(self.exchange).cancel_open_orders(self.symbol)

                # create notification
                evaluator_notification = None
                if self.notifier.enabled():
                    evaluator_notification = self.notifier.notify_state_changed(
                        self.final_eval,
                        self.symbol_evaluator.get_crypto_currency_evaluator(),
                        self.symbol_evaluator.get_symbol(),
                        self.symbol_evaluator.get_trader(self.exchange),
                        self.state,
                        self.symbol_evaluator.get_matrix(self.exchange).get_matrix())

                # call orders creation method
                self.create_final_state_orders(evaluator_notification)
