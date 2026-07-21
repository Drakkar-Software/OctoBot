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
import octobot_commons.enums as commons_enums
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator
import octobot_commons.dsl_interpreter.operator_parameter as dsl_interpreter_operator_parameter


class NaryOperator(
    dsl_interpreter_operator.Operator
):  # pylint: disable=abstract-method
    """
    Base class for n-ary operators.
    N-ary operators have one or more operands.
    """

    CATEGORY = commons_enums.DslKeywordCategory.LOGIC.value

    @classmethod
    def get_return_values(
        cls,
    ) -> list[dsl_interpreter_operator_parameter.OperatorParameter]:
        return cls.result_return_value(
            commons_enums.DslValueType.BOOLEAN.value,
            description="N-ary boolean operation result",
        )
