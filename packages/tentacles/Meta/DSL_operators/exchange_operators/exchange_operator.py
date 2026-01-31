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
import octobot_trading.exchanges

import octobot_commons.dsl_interpreter.operators.call_operator as dsl_interpreter_call_operator
import octobot_trading.modes.script_keywords as script_keywords


EXCHANGE_LIBRARY = "exchange"
UNINITIALIZED_VALUE = object()


class ExchangeOperator(dsl_interpreter_call_operator.CallOperator):

    @staticmethod
    def get_library() -> str:
        """
        Get the library of the operator.
        """
        return EXCHANGE_LIBRARY

    async def get_context(
        self, exchange_manager: octobot_trading.exchanges.ExchangeManager
    ) -> script_keywords.Context:
        # todo later: handle exchange manager without initialized trading modes
        return script_keywords.get_base_context(next(iter(exchange_manager.trading_modes)))
