#  Drakkar-Software OctoBot
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
import typing
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.signals as commons_signals

import octobot_trading.modes as trading_modes
import octobot_trading.enums as trading_enums

import tentacles.Meta.DSL_operators as dsl_operators


class DSLTradingModeConsumer(trading_modes.AbstractTradingModeConsumer):
    # should not be used
    pass


class DSLTradingModeProducer(trading_modes.AbstractTradingModeProducer):
    async def set_final_eval(
        self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame, trigger_source: str
    ):
        self.logger.info(
            f"Executing DSL script trigger by {matrix_id=}, {cryptocurrency=}, {symbol=}, {time_frame=}, {trigger_source=}"
        )
        result = await self.trading_mode.interpret_dsl_script() # type: ignore
        self.logger.info(f"DSL script successfully executed. Result: {result.result}")

    @classmethod
    def get_should_cancel_loaded_orders(cls) -> bool:
        """
        Called by cancel_symbol_open_orders => return true if OctoBot should cancel all orders for a symbol including
        orders already existing when OctoBot started up
        """
        return True


class DSLTradingMode(trading_modes.AbstractTradingMode):
    MODE_PRODUCER_CLASSES = [DSLTradingModeProducer]
    MODE_CONSUMER_CLASSES = [DSLTradingModeConsumer]
    DSL_SCRIPT = "dsl_script"

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.dsl_script: str = ""
        self.interpreter: dsl_interpreter.Interpreter = None # type: ignore

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        default_config = self.get_default_config()
        new_script = str(
            self.UI.user_input(
                self.DSL_SCRIPT, commons_enums.UserInputTypes.TEXT, default_config[self.DSL_SCRIPT],
                inputs, other_schema_values={"minLength": 0},
                title="DSL script: The DSL script to use for the trading mode."
            )
        )
        self.set_dsl_script(new_script, raise_on_error=False, dependencies=None)


    def set_dsl_script(
        self,
        dsl_script: str,
        raise_on_error: bool = True,
        dependencies: typing.Optional[commons_signals.SignalDependencies] = None
    ):
        if self.interpreter is None:
            self.interpreter = self._create_interpreter(dependencies)
        if self.dsl_script != dsl_script:
            self.dsl_script = dsl_script
            self.on_new_dsl_script(raise_on_error)

    def on_new_dsl_script(
        self, raise_on_error: bool = True,
    ):
        try:
            self.interpreter.prepare(self.dsl_script)
            self.logger.info(f"DSL script successfully loaded: '{self.dsl_script}'")
        except commons_errors.DSLInterpreterError as err:
            self.logger.exception(err, True, f"Error when parsing DSL script '{self.dsl_script}': {err}")
            if raise_on_error:
                raise err
        except Exception as err:
            self.logger.exception(err, True, f"Unexpected error when parsing DSL script '{self.dsl_script}': {err}")
            if raise_on_error:
                raise err

    def _create_interpreter(
        self, dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> dsl_interpreter.Interpreter:
        return dsl_interpreter.Interpreter(
            dsl_interpreter.get_all_operators()
            + dsl_operators.create_ohlcv_operators(self.exchange_manager, None, None)
            + dsl_operators.create_portfolio_operators(self.exchange_manager)
            + dsl_operators.create_create_order_operators(
                self.exchange_manager, trading_mode=self, dependencies=dependencies
            )
            + dsl_operators.create_cancel_order_operators(
                self.exchange_manager, trading_mode=self, dependencies=dependencies
            )
            + dsl_operators.create_blockchain_wallet_operators(self.exchange_manager)
        )

    async def interpret_dsl_script(self) -> dsl_interpreter.DSLCallResult:
        return await self.interpreter.compute_expression_with_result()

    async def stop(self):
        await super().stop()
        self.interpreter = None # type: ignore

    @classmethod
    def get_default_config(
        cls,
    ) -> dict:
        return {
            cls.DSL_SCRIPT: "",
        }

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return True

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
            trading_enums.ExchangeTypes.FUTURE,
        ]
