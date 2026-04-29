#  Drakkar-Software OctoBot-Commons
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
import octobot_commons.enums as enums
import octobot_commons.errors as errors


def evaluate_condition(left_operand, right_operand, operator: str) -> bool:
    """
    evaluates the given condition
    :param left_operand: the left operand of the condition
    :param right_operand: the right operand of the condition
    :param operator: the operator of the condition
    :return: True if the evaluated condition is True, False otherwise
    """
    if operator == enums.LogicalOperators.LOWER_THAN.value:
        return left_operand < right_operand
    if operator == enums.LogicalOperators.HIGHER_THAN.value:
        return left_operand > right_operand
    if operator == enums.LogicalOperators.LOWER_OR_EQUAL_TO.value:
        return left_operand <= right_operand
    if operator == enums.LogicalOperators.HIGHER_OR_EQUAL_TO.value:
        return left_operand >= right_operand
    if operator == enums.LogicalOperators.EQUAL_TO.value:
        return left_operand == right_operand
    if operator == enums.LogicalOperators.DIFFERENT_FROM.value:
        return left_operand != right_operand
    raise errors.LogicalOperatorError(f"Unknown operator: {operator}")
