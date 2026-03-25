# pylint: disable=missing-class-docstring,missing-function-docstring
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
import time

import octobot_commons.dsl_interpreter as dsl_interpreter


class NowMsOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 0
    MAX_PARAMS = 0
    NAME = "now_ms"
    DESCRIPTION = "Returns the current time in milliseconds since epoch."
    EXAMPLE = "now_ms()"

    @staticmethod
    def get_name() -> str:
        return "now_ms"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        return int(time.time() * 1000)
