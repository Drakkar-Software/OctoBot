from trading.trader.trader import *


class FinalEvaluator:
    def __init__(self, evaluator):
        self.evaluator = evaluator
        self.final_eval = START_EVAL_NOTE
        self.state = EvaluatorStates.NEUTRAL

    def set_state(self, state):
        if state != self.state:
            self.state = state
            if self.evaluator.notifier.enabled():
                self.evaluator.get_notifier().notify(self.evaluator.time_frame, self.evaluator.symbol, state)
            elif self.evaluator.trader.enabled():
                self.evaluator.get_evaluator_creator().create_order(self.evaluator.get_trader())
            elif self.evaluator.trader_simulator.enabled():
                self.evaluator.get_evaluator_creator().create_order(self.evaluator.get_trader_simulator())

    def get_state(self):
        return self.state

    def get_final_eval(self):
        return self.final_eval

    def prepare(self):
        rules_analysis_note_counter = 0
        # Rules analysis
        for evaluated_rules in self.evaluator.get_creator().get_rules_eval_list():
            self.final_eval += evaluated_rules.get_eval_note() * evaluated_rules.get_pertinence()
            rules_analysis_note_counter += evaluated_rules.get_pertinence()

        if rules_analysis_note_counter > 0:
            self.final_eval /= rules_analysis_note_counter
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
