#  Drakkar-Software OctoBot-Trading
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
import typing

import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.errors as commons_errors
import octobot_commons.configuration.user_inputs as user_inputs
import octobot_commons.logging as commons_logging

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.str_util as str_util
import octobot_trading.personal_data as personal_data
import octobot_trading.modes.modes_factory as modes_factory

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges
    import octobot_trading.modes.abstract_trading_mode


def _create_operator_parameters_from_user_inputs(
    created_user_inputs: dict,
) -> list[dsl_interpreter.OperatorParameter]:
    """
    Convert UserInput objects to OperatorParameter.
    Only includes top-level inputs (parent_input_name is None).
    """
    params = []
    for u_input in created_user_inputs.values():
        if not isinstance(u_input, user_inputs.UserInput):
            continue
        if u_input.parent_input_name is not None:
            continue
        input_type = (
            u_input.input_type
            if isinstance(u_input.input_type, str)
            else u_input.input_type.value
        )
        param_type = user_inputs.USER_INPUT_TYPE_TO_PYTHON_TYPE[input_type]
        param_name = user_inputs.sanitize_user_input_name(u_input.name)
        description = u_input.title or u_input.name
        params.append(
            dsl_interpreter.OperatorParameter(
                name=param_name,
                description=str(description),
                required=False,
                type=param_type,
                default=u_input.def_val,
            )
        )
    return params


def _create_trading_mode_operator_parameters(
    trading_mode_class: type,
    config: dict,
) -> list[dsl_interpreter.OperatorParameter]:
    """
    Derive operator parameters from the trading mode's init_user_inputs.
    Leverages inheritance: subclasses call super().init_user_inputs(inputs).
    """
    tentacles_setup_config = None
    loaded_config = {}
    tentacle_instance = trading_mode_class.create_local_instance(
        config, tentacles_setup_config, loaded_config
    )
    tentacle_instance.synchronous_execution = True
    created_user_inputs = {}
    tentacle_instance.init_user_inputs(created_user_inputs)
    return _create_operator_parameters_from_user_inputs(created_user_inputs)


class TradingModeOperator(
    dsl_interpreter.PreComputingCallOperator, dsl_interpreter.ReCallableOperatorMixin
):
    """
    Base DSL operator that instantiates and executes a trading mode when called.
    Subclasses are created dynamically by create_trading_mode_operator.
    """

    def __init__(
        self,
        *parameters: dsl_interpreter.OperatorParameterType,
        **kwargs: typing.Any,
    ):
        super().__init__(*parameters, **kwargs)
        self.param_by_name: dict[
            str, dsl_interpreter.ComputedOperatorParameterType
        ] = dsl_interpreter.UNINITIALIZED_VALUE  # type: ignore

    @staticmethod
    def get_library() -> str:
        return common_constants.CONTEXTUAL_OPERATORS_LIBRARY

    def get_exchange_manager(
        self,
    ) -> typing.Optional["octobot_trading.exchanges.ExchangeManager"]:
        raise NotImplementedError("get_exchange_manager must be implemented")

    def get_trading_mode_class(
        self,
    ) -> type:
        raise NotImplementedError("get_trading_mode_class must be implemented")

    def get_config(
        self,
    ) -> dict:
        raise NotImplementedError("get_config must be implemented")

    async def _optimize_initial_portfolio(
        self,
        trading_modes: list["octobot_trading.modes.abstract_trading_mode.AbstractTradingMode"],
        sellable_assets: list[str],
        tickers: dict,
    ) -> None:
        trading_mode = trading_modes[0]
        if not trading_mode.SUPPORTS_INITIAL_PORTFOLIO_OPTIMIZATION:
            self._get_logger().info(
                f"Trading mode {trading_mode.get_name()} does not support initial "
                f"portfolio optimization. Skipping optimization."
            )
            return
        exchange_manager = self.get_exchange_manager()
        balance_summary = personal_data.get_balance_summary(personal_data.portfolio_to_float(
            exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
        ), use_exchange_format=False)
        self._get_logger().info(
            f"Optimizing initial portfolio for trading mode {trading_mode.get_name()}. "
            f"Before optimization portfolio content: {balance_summary}"
        )
        await trading_mode.optimize_initial_portfolio(sellable_assets, tickers)
        balance_summary = personal_data.get_balance_summary(personal_data.portfolio_to_float(
            exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
        ), use_exchange_format=False)
        self._get_logger().info(
            f"Portfolio optimized for trading mode {trading_mode.get_name()}. "
            f"Post optimization portfolio content: {balance_summary}"
        )

    async def _create_trading_mode(
        self,
        trading_mode_class: type,
        trading_config: dict,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        symbol: str
    ) -> "octobot_trading.modes.abstract_trading_mode.AbstractTradingMode":
        trading_mode = trading_mode_class(exchange_manager.config, exchange_manager)
        if symbol is not None:
            trading_mode.symbol = symbol
        trading_mode.synchronous_execution = True
        await trading_mode.initialize(
            trading_config=trading_config,
            auto_start=False,
            previous_state=self.param_by_name.get("state")
        )
        for producer in trading_mode.producers:
            producer.force_is_ready_to_trade()
        return trading_mode

    async def _create_trading_modes(
        self,
        trading_mode_class: type,
        trading_config: dict,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
    ) -> list["octobot_trading.modes.abstract_trading_mode.AbstractTradingMode"]:
        trading_modes = []
        if trading_mode_class.get_is_symbol_wildcard():
            trading_mode = await self._create_trading_mode(
                trading_mode_class, trading_config, exchange_manager, None
            )
            trading_modes.append(trading_mode)
        else:
            for symbol in exchange_manager.exchange_config.traded_symbol_pairs:
                trading_mode = await self._create_trading_mode(
                    trading_mode_class, trading_config, exchange_manager, symbol
                )
                trading_modes.append(trading_mode)
        return trading_modes

    async def _execute_trading_mode(
        self, trading_mode: "octobot_trading.modes.abstract_trading_mode.AbstractTradingMode"
    ) -> dsl_interpreter.ReCallingOperatorResult:
        last_execution_time = time.time()
        await trading_mode.manual_trigger(
            {"trigger_source": common_enums.TriggerSource.MANUAL.value}
        )
        return self.create_re_callable_result(
            waiting_time=trading_mode.get_time_before_next_execution(),
            last_execution_time=last_execution_time,
            state=trading_mode.get_dsl_state(),
        )

    async def pre_compute(self) -> None:
        await super().pre_compute()
        exchange_manager = self.get_exchange_manager()
        if exchange_manager is None:
            raise commons_errors.DSLInterpreterError(
                "Exchange manager is required to execute trading mode operator"
            )
        self.param_by_name = self.get_computed_value_by_parameter()
        trading_modes = await self._create_trading_modes(
            self.get_trading_mode_class(),
            self.param_by_name,
            exchange_manager
        )
        if not self.get_last_execution_result(self.param_by_name):
            try:
                # this is the first execution, optimize initial portfolio
                sellable_assets = [] # todo later: populate with asseets that can be sold additionally to the traded ones
                tickers = {}
                await self._optimize_initial_portfolio(trading_modes, sellable_assets, tickers)
            except Exception as err:
                self._get_logger().exception(err, True, f"Error when optimizing initial portfolio: {err}")

        recallable_results: list[dsl_interpreter.ReCallingOperatorResult] = []
        for trading_mode in trading_modes:
            recallable_result = await self._execute_trading_mode(trading_mode)
            recallable_results.append(recallable_result)
        self.value = self.get_results_summary(recallable_results)

    def get_results_summary(
        self, recallable_results: list[dsl_interpreter.ReCallingOperatorResult]
    ) -> dict:
        waiting_with_last_exec: list[tuple[typing.Any, typing.Any]] = []
        merged_state: dict[str, typing.Any] = {}
        for result in recallable_results:
            if not result.last_execution_result:
                continue
            if waiting_time := result.last_execution_result.get(
                dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value
            ):
                last_execution_time = result.last_execution_result.get(
                    dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value
                )
                waiting_with_last_exec.append((waiting_time, last_execution_time))
            merged_state.update(result.last_execution_result)

        if not waiting_with_last_exec:
            min_waiting_time = None
            summary_last_execution_time = None
        else:
            min_waiting_time, summary_last_execution_time = min(
                waiting_with_last_exec, key=lambda element: element[0]
            )

        return self.create_re_callable_result_dict(
            waiting_time=min_waiting_time or None,
            last_execution_time=summary_last_execution_time or None,
            state=merged_state,
        )

    def get_dependencies(self) -> typing.List[dsl_interpreter.InterpreterDependency]:
        trading_mode_class = self.get_trading_mode_class()
        param_by_name = self.get_computed_value_by_parameter()
        local_dependencies = trading_mode_class.get_dsl_dependencies(
            param_by_name, self.get_config()
        )
        return super().get_dependencies() + local_dependencies

    def _get_logger(self) -> commons_logging.BotLogger:
        return commons_logging.get_logger(f"{self.get_trading_mode_class().get_name()}Operator")

    
def create_trading_mode_operator(
    trading_mode_class: type,
    exchange_manager: typing.Optional["octobot_trading.exchanges.ExchangeManager"],
    config: dict,
) -> type:
    """
    Create a DSL operator class that, when called, instantiates and executes
    the given trading mode.
    :param trading_mode_class: The trading mode class to execute
    :param exchange_manager: The exchange manager to use for execution
    :return: A DSL operator class for registration with an Interpreter
    """
    _operator_parameters: list[dsl_interpreter.OperatorParameter] = []
    operator_name = str_util.camel_to_snake(trading_mode_class.get_name())

    class _ContextProviderMixin:
        def get_exchange_manager(
            self,
        ) -> typing.Optional[
            "octobot_trading.exchanges.ExchangeManager"
        ]:
            return exchange_manager

        def get_trading_mode_class(self) -> type:
            return trading_mode_class

        def get_config(self) -> dict:
            return config

    class _TradingModeOperatorImpl(
        _ContextProviderMixin, TradingModeOperator
    ):
        DESCRIPTION = f"Executes the {trading_mode_class.get_name()} trading mode"
        EXAMPLE = f"{operator_name}()"

        @staticmethod
        def get_name() -> str:
            return operator_name

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            if not _operator_parameters:
                # lazy computation of the operator parameters to only compute them once 
                # and when the operator is actually used (and not just when instantiated)
                _operator_parameters.extend(_create_trading_mode_operator_parameters(
                    trading_mode_class, config #, tentacles_setup_config, loaded_config
                ))
            return _operator_parameters + cls.get_re_callable_parameters()

    return _TradingModeOperatorImpl


def create_all_trading_mode_operators(
    exchange_manager: typing.Optional["octobot_trading.exchanges.ExchangeManager"],
    config: dict,
) -> list[type]:
    """
    Create DSL operators for all available trading modes.
    :param exchange_manager: The exchange manager to use for trading mode execution
    :return: List of DSL operator classes for registration with an Interpreter
    """

    operators = []
    for trading_mode_class in modes_factory.get_all_concrete_trading_mode_classes():
        operators.append(
            create_trading_mode_operator(trading_mode_class, exchange_manager, config)
        )
    return operators
