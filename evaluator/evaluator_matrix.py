from config.cst import EvaluatorMatrixTypes, CONFIG_DEBUG_MATRIX_HISTORY, CONFIG_DEBUG_MATRIX_HISTORY_FILE


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

        if EvaluatorMatrixHistory.enabled(self.config):
            EvaluatorMatrixHistory.update_history(self.matrix)

    def get_type_evals(self, matrix_type):
        return self.matrix[matrix_type]

    def get_matrix(self):
        return self.matrix


class EvaluatorMatrixHistory:
    @staticmethod
    def update_history(matrix):
        with open(CONFIG_DEBUG_MATRIX_HISTORY_FILE, "a") as file:
            file.write(matrix)

    @staticmethod
    def enabled(config):
        if CONFIG_DEBUG_MATRIX_HISTORY in config and config[CONFIG_DEBUG_MATRIX_HISTORY]:
            return True
        else:
            return False
