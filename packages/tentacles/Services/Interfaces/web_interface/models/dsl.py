#  Drakkar-Software OctoBot-Interfaces
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

import tentacles.Meta.DSL_operators.exchange_operators as dsl_operators


def get_dsl_keywords_docs() -> list[dsl_interpreter.OperatorDocs]:
    all_operators = (
        dsl_interpreter.get_all_operators()
        + dsl_operators.create_ohlcv_operators(
            None, None, None
        )
        + dsl_operators.create_portfolio_operators(
            None
        )
        + dsl_operators.create_create_order_operators(
            None,
        )
        + dsl_operators.create_cancel_order_operators(
            None,
        )
    )
    return [
        operator.get_docs() 
        for operator in all_operators
    ]
