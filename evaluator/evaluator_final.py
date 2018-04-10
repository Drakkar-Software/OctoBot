from config.cst import START_EVAL_NOTE, EvaluatorStates


class FinalEvaluator:
    def __init__(self, symbol_evaluator):
        self.symbol_evaluator = symbol_evaluator
        self.final_eval = START_EVAL_NOTE
        self.state = EvaluatorStates.NEUTRAL

    def set_state(self, exchange, symbol, state):
        if state != self.state:
            self.state = state
            if self.symbol_evaluator.notifier.enabled():
                self.symbol_evaluator.get_notifier().notify(self.symbol_evaluator.crypto_currency, state)

            elif self.symbol_evaluator.get_trader(exchange).enabled():
                self.symbol_evaluator.get_evaluator_creator().create_order(
                    symbol,
                    exchange,
                    self.symbol_evaluator.get_trader(exchange),
                    state)

            elif self.symbol_evaluator.get_trader_simulator(exchange).enabled():
                self.symbol_evaluator.get_evaluator_creator().create_order(
                    symbol,
                    exchange,
                    self.symbol_evaluator.get_trader_simulator(exchange),
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

    def create_state(self, exchange, symbol):
        # TODO : improve
        if self.final_eval < -0.6:
            self.set_state(exchange, symbol, EvaluatorStates.VERY_LONG)
        elif self.final_eval < -0.2:
            self.set_state(exchange, symbol, EvaluatorStates.LONG)
        elif self.final_eval < 0.2:
            self.set_state(exchange, symbol, EvaluatorStates.NEUTRAL)
        elif self.final_eval < 0.6:
            self.set_state(exchange, symbol, EvaluatorStates.SHORT)
        else:
            self.set_state(exchange, symbol, EvaluatorStates.VERY_SHORT)
