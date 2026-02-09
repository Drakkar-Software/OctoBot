#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import typing

import octobot_commons.configuration as configuration
import octobot_trading.api as trading_api
import octobot_commons.enums as commons_enums
import octobot.automation.bases.abstract_condition as abstract_condition
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot.errors as errors
import tentacles.Meta.DSL_operators as dsl_operators
import octobot.automation.bases.execution_details as execution_details



class ScriptedCondition(abstract_condition.AbstractCondition):
    SCRIPT = "script"
    EXCHANGE = "exchange"

    def __init__(self):
        super().__init__()
        self.script: str = ""
        self.exchange_name: str = ""

        self._dsl_interpreter: typing.Optional[dsl_interpreter.Interpreter] = None

    async def process(self, execution_details: execution_details.ExecutionDetails) -> bool:
        if self._dsl_interpreter:
            script_result = await self._dsl_interpreter.interprete(self.script)
            return bool(script_result)
        raise errors.InvalidAutomationConfigError("Scripted condition is not properly configured, the script is likely invalid.", self.get_name())

    @staticmethod
    def get_description() -> str:
        return "Evaluates a scripted condition using the OctoBot DSL."

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        exchanges = list(trading_api.get_exchange_names())
        return {
            self.SCRIPT: UI.user_input(
                self.SCRIPT, commons_enums.UserInputTypes.TEXT, "", inputs,
                title="Scripted condition: the OctoBot DSL expression to evaluate (more info in automation details). Its return value will be converted to a boolean using \"bool()\" to determine if the condition is met.",
                parent_input_name=step_name,
            ),
            self.EXCHANGE: UI.user_input(
                self.EXCHANGE, commons_enums.UserInputTypes.OPTIONS, exchanges[0] if exchanges[0] else "binance", inputs,
                options=exchanges,
                title="Exchange: the name of the exchange to use for the condition.",
                parent_input_name=step_name,
            )
        }

    def apply_config(self, config):
        self.script = config[self.SCRIPT]
        self.exchange_name = config[self.EXCHANGE]
        if self.script and self.exchange_name:
            self._dsl_interpreter = self._create_dsl_interpreter()
            self._validate_script()
        else:
            self._dsl_interpreter = None
    
    def _validate_script(self):
        try:
            self._dsl_interpreter.prepare(self.script)
            self.logger.info(
                f"Formula interpreter successfully prepared \"{self.script}\" condition"
            )
        except Exception as e:
            self.logger.error(f"Error when parsing condition {self.script}: {e}")
            raise e

    def _create_dsl_interpreter(self):
        exchange_manager = self._get_exchange_manager()
        ohlcv_operators = []
        portfolio_operators = []
        if exchange_manager is not None:
            ohlcv_operators = dsl_operators.exchange_operators.create_ohlcv_operators(
                exchange_manager, None, None
            )
            portfolio_operators = dsl_operators.exchange_operators.create_portfolio_operators(
                exchange_manager
            )
        return dsl_interpreter.Interpreter(
            dsl_interpreter.get_all_operators() + ohlcv_operators + portfolio_operators
        )
    
    def _get_exchange_manager(self):
        for exchange_id in trading_api.get_exchange_ids():
            exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            if exchange_manager.exchange_name == self.exchange_name and exchange_manager.is_backtesting == False:
                return exchange_manager
        raise errors.InvalidAutomationConfigError(f"No exchange manager found for exchange name: {self.exchange_name}", self.get_name())
