class EvaluationMatrix:

    def __init__(self):
        self.social_eval_value_dict = {}
        self.TA_eval_value_dict = {}

# ---- getters and setter ----
    def set_social_eval(self, evaluator_name, value):
        self.social_eval_value_dict[evaluator_name] = value

    def set_TA_eval(self, evaluator_name, value):
        self.TA_eval_value_dict[evaluator_name] = value

    def get_social_evals(self):
        return self.social_eval_value_dict

    def get_TA_evals(self):
        return self.TA_eval_value_dict
