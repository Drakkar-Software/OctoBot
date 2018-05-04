from config.cst import EvaluatorMatrixTypes
from tools.evaluators_util import check_valid_eval_note


class EvaluatorMatrix:
    def __init__(self, config):
        self.config = config
        self.matrix = {
            EvaluatorMatrixTypes.TA: {},
            EvaluatorMatrixTypes.SOCIAL: {},
            EvaluatorMatrixTypes.REAL_TIME: {},
            EvaluatorMatrixTypes.STRATEGIES: {}
        }

    # ---- getters and setters----
    def set_eval(self, matrix_type, evaluator_name, value, time_frame=None):
        if evaluator_name not in self.matrix[matrix_type]:
            self.matrix[matrix_type][evaluator_name] = {}

        if time_frame:
            self.matrix[matrix_type][evaluator_name][time_frame] = value
        else:
            self.matrix[matrix_type][evaluator_name] = value

    def get_type_evals(self, matrix_type):
        return self.matrix[matrix_type]

    @staticmethod
    def get_eval_note(matrix, matrix_type, evaluator_name, time_frame=None):
        if matrix_type in matrix and evaluator_name in matrix[matrix_type]:
            if time_frame is not None:
                if time_frame in matrix[matrix_type][evaluator_name]:
                    eval_note = matrix[matrix_type][evaluator_name][time_frame]
                    if check_valid_eval_note(eval_note):
                        return eval_note
            else:
                eval_note = matrix[matrix_type][evaluator_name]
                if check_valid_eval_note(eval_note):
                    return eval_note
        return None

    def get_matrix(self):
        return self.matrix
