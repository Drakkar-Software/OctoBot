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


class FitnessParameter:
    NAME_KEY = "name"
    WEIGHT_KEY = "weight"
    IS_RATIO_FROM_MAX_KEY = "is_ratio_from_max"

    def __init__(self, name, weight, is_ratio_from_max):
        self.name = name
        self.weight = weight
        self.is_ratio_from_max = is_ratio_from_max
        self.max_ratio_value = None

    def get_normalized_value(self, raw_value):
        normalized_value = raw_value * self._get_parameter_normalizer() * self.weight
        if self.is_ratio_from_max:
            # use ratio if relevant
            return normalized_value / (self.max_ratio_value * self._get_parameter_normalizer()) \
                if self.max_ratio_value else normalized_value
        return normalized_value

    def _get_parameter_normalizer(self):
        return 0.01 if "%" in self.name else 1

    def update_max_ratio(self, full_result):
        try:
            if self.max_ratio_value is None or full_result[self.name] > self.max_ratio_value:
                self.max_ratio_value = full_result[self.name]
        except KeyError:
            pass

    @classmethod
    def from_dict(cls, param_dict):
        return cls(
            param_dict[cls.NAME_KEY],
            param_dict[cls.WEIGHT_KEY],
            param_dict[cls.IS_RATIO_FROM_MAX_KEY],
        )
