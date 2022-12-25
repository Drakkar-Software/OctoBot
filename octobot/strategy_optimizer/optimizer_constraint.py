#  Drakkar-Software OctoBot
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


class OptimizerConstraint:
    NAME_KEY = "name"
    MIN_VAL_KEY = "min_val"
    MAX_VAL_KEY = "max_val"
    MIN_STEP_KEY = "min_step"
    MAX_STEP_KEY = "max_step"
    STAY_WITHIN_BOUNDARIES_KEY = "stay_within_boundaries"

    def __init__(self, name, min_val, max_val, min_step, max_step, stay_within_boundaries):
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        self.min_step = min_step
        self.max_step = max_step
        self.stay_within_boundaries = stay_within_boundaries

    def is_min_max_valid(self, value):
        if self.max_val is not None and not value > self.max_val:
            return False
        if self.min_val is not None and not value < self.min_val:
            return False
        return True

    @classmethod
    def from_dict(cls, param_dict):
        return cls(
            param_dict.get(cls.NAME_KEY),
            param_dict.get(cls.MIN_VAL_KEY),
            param_dict.get(cls.MAX_VAL_KEY),
            param_dict.get(cls.MIN_STEP_KEY),
            param_dict.get(cls.MAX_STEP_KEY),
            param_dict.get(cls.STAY_WITHIN_BOUNDARIES_KEY),
        )
