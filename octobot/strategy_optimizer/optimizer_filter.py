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
import decimal
import octobot_commons.logical_operators as logical_operators


class OptimizerFilter:
    LEFT_OPERAND_KEY_KEY = "left_operand_key"
    RIGHT_OPERAND_KEY_KEY = "right_operand_key"
    LEFT_OPERAND_VALUE_KEY = "left_operand_value"
    RIGHT_OPERAND_VALUE_KEY = "right_operand_value"
    OPERATOR_KEY = "operator"

    def __init__(self, left_operand_key, right_operand_key, left_operand_value, right_operand_value, operator):
        self.left_operand_key = left_operand_key
        self.right_operand_key = right_operand_key
        self.left_operand_value = left_operand_value
        self.right_operand_value = right_operand_value
        self.operator = operator

    def is_valid(self):
        return self.left_operand_value and self.right_operand_value and self.operator

    def load_values(self, values: dict):
        succeeded = False
        if self.left_operand_key is not None:
            try:
                self.left_operand_value = values[self.left_operand_key]
                succeeded = True
            except KeyError:
                pass
        if self.right_operand_key is not None:
            try:
                self.right_operand_value = values[self.right_operand_key]
            except KeyError:
                if not succeeded:
                    # require at least one value read
                    raise

    def is_filtered(self):
        if not self.is_valid():
            return False
        try:
            left_operand = decimal.Decimal(self.left_operand_value)
        except decimal.InvalidOperation:
            left_operand = str(self.left_operand_value)
        try:
            right_operand = decimal.Decimal(self.right_operand_value)
        except decimal.InvalidOperation:
            right_operand = str(self.right_operand_value)
        return logical_operators.evaluate_condition(left_operand, right_operand, self.operator)

    @classmethod
    def from_dict(cls, param_dict):
        return cls(
            param_dict[cls.LEFT_OPERAND_KEY_KEY],
            param_dict[cls.RIGHT_OPERAND_KEY_KEY],
            param_dict[cls.LEFT_OPERAND_VALUE_KEY],
            param_dict[cls.RIGHT_OPERAND_VALUE_KEY],
            param_dict[cls.OPERATOR_KEY],
        )
