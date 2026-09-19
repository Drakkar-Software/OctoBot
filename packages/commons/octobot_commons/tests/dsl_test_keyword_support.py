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

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.enums as commons_enums


class TestKeywordMixin:
    """
    Catalog defaults for module-level test Operator subclasses.

    pytest-xdist can import test modules before /api/v1/dsl/keywords tests; incomplete
    operators used to make operator_docs_to_dsl_keyword() raise and return HTTP 500.
    Inherit this mixin first on test operators that only implement get_name() / compute().
    """

    CATEGORY = commons_enums.DslKeywordCategory.LOGIC.value
    DESCRIPTION = "Test-only DSL operator."
    EXAMPLE = ""

    @classmethod
    def get_return_values(cls) -> list[dsl_interpreter.OperatorParameter]:
        return dsl_interpreter.Operator.result_return_value(
            commons_enums.DslValueType.ANY.value,
            description="Test operator result",
        )


class TestKeywordOperator(TestKeywordMixin, dsl_interpreter.Operator):
    """Minimal test operator base with catalog-safe defaults."""

    __test__ = False

    @staticmethod
    def get_name() -> str:
        raise NotImplementedError("get_name is not implemented")

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        raise NotImplementedError("compute is not implemented")
