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
import octobot_commons.errors
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator


class NestedInterpretationMixin:
    """
    Mixin for operators that interpret nested DSL strings using the parent
    interpreter's operator registry (see Operator.interpreter).
    """

    async def interprete_in_nested_interpreter(
        self, expression: str
    ) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        """
        Interprets the given expression in the nested interpreter.
        """
        if self.interpreter is None: # type: ignore
            raise octobot_commons.errors.DSLInterpreterError(
                "Cannot interpret nested expression: no parent interpreter was provided"
            )
        nested_interpreter = self.interpreter.create_nested() # type: ignore
        return await nested_interpreter.interprete(expression)
