import logging

from tools.evaluators_util import check_valid_eval_note


class EvaluatorDivergenceAnalyser:
    def __init__(self):
        self.average_note = None
        self.average_counter = None
        self.matrix = None

        self.DIVERGENCE_THRESHOLD = 0.25

        self.logger = logging.getLogger(self.__class__.__name__)

    def update(self, matrix):
        self.average_note = 0
        self.average_counter = 0
        self.matrix = matrix

        self.calculate_matrix_evaluators_average()

        if self.average_counter > 0:
            self.average_note /= self.average_counter

            self.check_matrix_divergence()

    def calculate_matrix_evaluators_average(self):
        for matrix_type in self.matrix:
            for evaluator_name in self.matrix[matrix_type]:
                if isinstance(self.matrix[matrix_type][evaluator_name], dict):
                    for time_frame in self.matrix[matrix_type][evaluator_name]:
                        self.add_to_average(self.matrix[matrix_type][evaluator_name][time_frame])
                else:
                    self.add_to_average(self.matrix[matrix_type][evaluator_name])

    def add_to_average(self, value):
        # Todo check evaluator pertinence
        self.average_note += value
        self.average_counter += 1

    def check_matrix_divergence(self):
        for matrix_type in self.matrix:
            for evaluator_name in self.matrix[matrix_type]:
                if isinstance(self.matrix[matrix_type][evaluator_name], dict):
                    for time_frame in self.matrix[matrix_type][evaluator_name]:
                        if check_valid_eval_note(
                                self.matrix[matrix_type][evaluator_name][time_frame]):
                            if self.check_eval_note_divergence(self.matrix[matrix_type][evaluator_name][time_frame]):
                                self.log_divergence(matrix_type,
                                                    evaluator_name,
                                                    self.matrix[matrix_type][evaluator_name][time_frame],
                                                    time_frame)
                else:
                    if check_valid_eval_note(self.matrix[matrix_type][evaluator_name]):
                        if self.check_eval_note_divergence(self.matrix[matrix_type][evaluator_name]):
                            self.log_divergence(matrix_type,
                                                evaluator_name,
                                                self.matrix[matrix_type][evaluator_name])

    def check_eval_note_divergence(self, eval_note):
        if self.average_note <= 0:
            if self.average_note + self.DIVERGENCE_THRESHOLD < eval_note < self.average_note - self.DIVERGENCE_THRESHOLD:
                return False
        else:
            if self.average_note + self.DIVERGENCE_THRESHOLD > eval_note > self.average_note - self.DIVERGENCE_THRESHOLD:
                return False
        return True

    def log_divergence(self, matrix_type, evaluator_name, eval_note, time_frame=None):
        self.logger.warning("Divergence detected on {0} {1} {2} | Average : {3} -> Eval : {4} ".format(matrix_type,
                                                                                                       evaluator_name,
                                                                                                       time_frame,
                                                                                                       self.average_note,
                                                                                                       eval_note))
