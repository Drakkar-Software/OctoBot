#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import numpy

import octobot_commons.constants as commons_constants


class OverallStateAnalyser:
    def __init__(self):
        self.overall_state = commons_constants.START_PENDING_EVAL_NOTE
        self.evaluation_count = 0
        self.evaluations = []

    # evaluation: number between -1 and 1
    # weight: integer between 0 (not even taken into account) and X
    def add_evaluation(self, evaluation, weight, refresh_overall_state=True):
        self.evaluations.append(StateEvaluation(evaluation, weight))
        if refresh_overall_state:
            self._refresh_overall_state()

    def get_overall_state_after_refresh(self, refresh_overall_state=True):
        if refresh_overall_state:
            self._refresh_overall_state()
        return self.overall_state

    # computes self.overall_state using self.evaluations values and weights
    def _refresh_overall_state(self):
        if self.evaluations:
            self.overall_state = numpy.mean(
                [evaluation.value for evaluation in self.evaluations for _ in range(evaluation.weight)]
            )


class StateEvaluation:
    def __init__(self, value, weight):
        self.value = value
        self.weight = weight
