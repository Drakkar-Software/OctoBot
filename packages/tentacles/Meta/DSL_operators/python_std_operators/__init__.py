# pylint: disable=R0801
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

import tentacles.Meta.DSL_operators.python_std_operators.base_binary_operators as dsl_interpreter_base_binary_operators
from tentacles.Meta.DSL_operators.python_std_operators.base_binary_operators import (
    AddOperator,
    SubOperator,
    MultOperator,
    DivOperator,
    FloorDivOperator,
    ModOperator,
    PowOperator,
)
import tentacles.Meta.DSL_operators.python_std_operators.base_compare_operators as dsl_interpreter_base_compare_operators
from tentacles.Meta.DSL_operators.python_std_operators.base_compare_operators import (
    EqOperator,
    NotEqOperator,
    LtOperator,
    LtEOperator,
    GtOperator,
    GtEOperator,
    IsOperator,
    IsNotOperator,
    InOperator,
    NotInOperator,
)
import tentacles.Meta.DSL_operators.python_std_operators.base_unary_operators as dsl_interpreter_base_unary_operators
from tentacles.Meta.DSL_operators.python_std_operators.base_unary_operators import (
    UAddOperator,
    USubOperator,
    NotOperator,
    InvertOperator,
)
import tentacles.Meta.DSL_operators.python_std_operators.base_nary_operators as dsl_interpreter_base_nary_operators
from tentacles.Meta.DSL_operators.python_std_operators.base_nary_operators import (
    AndOperator,
    OrOperator,
)
import tentacles.Meta.DSL_operators.python_std_operators.base_call_operators as dsl_interpreter_base_call_operators
from tentacles.Meta.DSL_operators.python_std_operators.base_call_operators import (
    MinOperator,
    MaxOperator,
    MeanOperator,
    SqrtOperator,
    AbsOperator,
    RoundOperator,
    FloorOperator,
    CeilOperator,
    SinOperator,
    CosOperator,
    OscillatorOperator,
)
import tentacles.Meta.DSL_operators.python_std_operators.base_name_operators as dsl_interpreter_base_name_operators
from tentacles.Meta.DSL_operators.python_std_operators.base_name_operators import (
    PiOperator,
)
import tentacles.Meta.DSL_operators.python_std_operators.base_expression_operators as dsl_interpreter_base_expression_operators
from tentacles.Meta.DSL_operators.python_std_operators.base_expression_operators import (
    IfExpOperator,
)
import tentacles.Meta.DSL_operators.python_std_operators.base_subscripting_operators as dsl_interpreter_base_subscripting_operators
from tentacles.Meta.DSL_operators.python_std_operators.base_subscripting_operators import (
    SubscriptOperator,
    SliceOperator,
)
import tentacles.Meta.DSL_operators.python_std_operators.base_iterable_operators as dsl_interpreter_base_iterable_operators
from tentacles.Meta.DSL_operators.python_std_operators.base_iterable_operators import (
    ListOperator,
)

__all__ = [
    "AddOperator",
    "SubOperator",
    "MultOperator",
    "DivOperator",
    "FloorDivOperator",
    "ModOperator",
    "PowOperator",
    "EqOperator",
    "NotEqOperator",
    "LtOperator",
    "LtEOperator",
    "GtOperator",
    "GtEOperator",
    "IsOperator",
    "IsNotOperator",
    "InOperator",
    "NotInOperator",
    "UAddOperator",
    "USubOperator",
    "NotOperator",
    "InvertOperator",
    "AndOperator",
    "OrOperator",
    "MinOperator",
    "MaxOperator",
    "MeanOperator",
    "SqrtOperator",
    "AbsOperator",
    "RoundOperator",
    "FloorOperator",
    "CeilOperator",
    "SinOperator",
    "CosOperator",
    "OscillatorOperator",
    "PiOperator",
    "IfExpOperator",
    "SubscriptOperator",
    "SliceOperator",
    "ListOperator",
]
