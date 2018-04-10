from config.cst import EvaluatorMatrixTypes


class EvaluatorMatrix:
    def __init__(self):
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

    def get_matrix(self):
        return self.matrix
