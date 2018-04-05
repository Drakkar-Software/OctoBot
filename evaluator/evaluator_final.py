from config.cst import *
from exchanges.trader import *


class FinalEvaluator:
    def __init__(self, evaluator):
        self.evaluator = evaluator
        self.final_eval = START_EVAL_NOTE
        self.social_final_eval = START_EVAL_NOTE
        self.ta_final_eval = START_EVAL_NOTE
        self.state = EvaluatorStates.NEUTRAL

    def set_state(self, state):
        if state != self.state:
            self.state = state
            if self.evaluator.notifier.enabled():
                self.evaluator.get_notifier().notify(self.evaluator.time_frame, self.evaluator.symbol, state)
            else:
                # TODO : prepare trade
                self.evaluator.get_trader().create_order(TraderOrderType.BUY_LIMIT)

    def get_state(self):
        return self.state

    def get_final_eval(self):
        return self.final_eval

    def prepare(self):
        ta_analysis_note_counter = 0
        # TA analysis
        for evaluated in self.evaluator.get_creator().get_ta_eval_list():
            self.ta_final_eval += evaluated.get_eval_note() * evaluated.get_pertinence()
            ta_analysis_note_counter += evaluated.get_pertinence()

        if ta_analysis_note_counter > 0:
            self.ta_final_eval /= ta_analysis_note_counter
        else:
            self.ta_final_eval = START_EVAL_NOTE

        # Social analysis
        social_analysis_note_counter = 0
        for evaluated in self.evaluator.get_creator().get_social_eval_list():
            self.social_final_eval += evaluated.get_eval_note() * evaluated.get_pertinence()
            social_analysis_note_counter += evaluated.get_pertinence()

        if social_analysis_note_counter > 0:
            self.social_final_eval /= social_analysis_note_counter
        else:
            self.social_final_eval = START_EVAL_NOTE

    def calculate_final(self):
        # TODO : improve
        self.final_eval = (self.ta_final_eval * EvaluatorsPertinence.TAEvaluator.value
                           + self.social_final_eval * EvaluatorsPertinence.SocialEvaluator.value)
        self.final_eval /= (EvaluatorsPertinence.TAEvaluator.value + EvaluatorsPertinence.SocialEvaluator.value)

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
