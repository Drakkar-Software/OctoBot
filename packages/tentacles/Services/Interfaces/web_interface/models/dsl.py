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
import octobot_services.interfaces.util as interfaces_util

import tentacles.Meta.DSL_operators.exchange_operators as dsl_operators


def get_dsl_keywords_docs() -> list[dsl_interpreter.OperatorDocs]:
    exchange_managers = interfaces_util.get_exchange_managers()
    all_operators = list(dsl_interpreter.get_all_operators()) # copy list to avoid modifying the original (cached) list
    if exchange_managers:
        # include exchange related operators
        all_operators += dsl_operators.create_ohlcv_operators(
            exchange_managers[0], None, None
        )
        all_operators += dsl_operators.create_portfolio_operators(
            exchange_managers[0]
        )
    return [
        operator.get_docs() 
        for operator in all_operators
    ]
