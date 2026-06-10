#  Drakkar-Software OctoBot-Evaluators
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

import octobot_commons.constants as common_constants
import octobot_commons.databases as commons_databases
import octobot_commons.enums as common_enums
import octobot_commons.errors as commons_errors
import octobot_commons.configuration.user_inputs as user_inputs
import octobot_commons.logging as commons_logging
import octobot_commons.tentacles_management as tentacles_management
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.str_util as str_util
import octobot_commons.symbols as symbols_util
import octobot_commons.list_util as list_util

import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.evaluators.evaluator_factory as evaluator_factory
import octobot_evaluators.util.evaluator_result as evaluator_result
import octobot_evaluators.enums as evaluators_enums
import octobot_evaluators.constants as evaluators_constants
import octobot_evaluators.matrix.matrix_manager as matrix_manager

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


SYMBOLS_PARAM = "symbols"
TIME_FRAMES_PARAM = "time_frames"
CRYPTOCURRENCY_PARAM = "cryptocurrency"
INCLUDE_IN_CONSTRUCTION_CANDLE_PARAM = "include_in_construction_candle"
DSL_BOT_ID = "dsl"
DSL_STORAGE_CLASS_NAME = "DSL"

EvaluatorResult = evaluator_result.EvaluatorResult


def _create_operator_parameters_from_user_inputs(
    created_user_inputs: dict,
) -> list[dsl_interpreter.OperatorParameter]:
    params = []
    for user_input in created_user_inputs.values():
        if not isinstance(user_input, user_inputs.UserInput):
            continue
        if user_input.parent_input_name is not None:
            continue
        input_type = (
            user_input.input_type
            if isinstance(user_input.input_type, str)
            else user_input.input_type.value
        )
        param_type = user_inputs.USER_INPUT_TYPE_TO_PYTHON_TYPE[input_type]
        param_name = user_inputs.sanitize_user_input_name(user_input.name)
        description = user_input.title or user_input.name
        params.append(
            dsl_interpreter.OperatorParameter(
                name=param_name,
                description=str(description),
                required=False,
                type=param_type,
                default=user_input.def_val,
            )
        )
    return params


class _LocalTentaclesSetupConfig:
    def is_tentacle_activated(self, _klass_name) -> bool:
        return True


def _get_local_tentacles_setup_config():
    return _LocalTentaclesSetupConfig()


async def _ensure_dsl_bot_storage_registered() -> None:
    # disable evaluator storage operations for DSL calls
    await commons_databases.init_bot_storage(
        DSL_BOT_ID,
        commons_databases.RunDatabasesIdentifier(
            tentacle_class=DSL_STORAGE_CLASS_NAME,
            enable_storage=False,
        ),
        clear_user_inputs=False,
    )


def _create_evaluator_operator_parameters(
    evaluator_class: type,
    config: dict,
) -> list[dsl_interpreter.OperatorParameter]:
    tentacles_setup_config = _get_local_tentacles_setup_config()
    loaded_config = {}
    tentacle_instance = evaluator_class.create_local_instance(
        config, tentacles_setup_config, loaded_config
    )
    created_user_inputs = {}
    tentacle_instance.init_user_inputs(created_user_inputs)
    return _create_operator_parameters_from_user_inputs(created_user_inputs)


def _normalize_time_frame_value(time_frame) -> str:
    if isinstance(time_frame, common_enums.TimeFrames):
        return time_frame.value
    return str(time_frame)


def _get_cryptocurrency_from_symbol(
    symbol: typing.Optional[str],
    cryptocurrency: typing.Optional[str],
) -> typing.Optional[str]:
    if cryptocurrency is not None:
        return cryptocurrency
    if symbol is None:
        return None
    return symbols_util.parse_symbol(symbol).base


def _seed_matrix_from_injected_evaluator_result(
    matrix_id: str,
    exchange_name: str,
    injected_result: EvaluatorResult,
) -> None:
    if injected_result.evaluator_name is None or injected_result.eval_note is None:
        return
    tentacle_path = matrix_manager.get_matrix_default_value_path(
        injected_result.evaluator_name,
        injected_result.evaluator_type,
        exchange_name=exchange_name,
        cryptocurrency=injected_result.cryptocurrency,
        symbol=injected_result.symbol,
        time_frame=injected_result.time_frame,
    )
    matrix_manager.set_tentacle_value(
        matrix_id,
        tentacle_path,
        evaluators_constants.EVALUATOR_EVAL_DEFAULT_TYPE,
        injected_result.eval_note,
    )


class EvaluatorOperator(
    dsl_interpreter.PreComputingCallOperator,
    dsl_interpreter.ReCallableOperatorMixin,
    dsl_interpreter.DynamicDependenciesOperatorMixin,
):
    def __init__(
        self,
        *parameters: dsl_interpreter.OperatorParameterType,
        **kwargs: typing.Any,
    ):
        super(dsl_interpreter.PreComputingCallOperator, self).__init__(*parameters, **kwargs)

    @staticmethod
    def get_library() -> str:
        return common_constants.CONTEXTUAL_OPERATORS_LIBRARY

    def get_exchange_manager(
        self,
    ) -> typing.Optional["octobot_trading.exchanges.ExchangeManager"]:
        raise NotImplementedError("get_exchange_manager must be implemented")

    def get_evaluator_class(self) -> type:
        raise NotImplementedError("get_evaluator_class must be implemented")

    def get_config(self) -> dict:
        raise NotImplementedError("get_config must be implemented")

    def get_matrix_id(self) -> typing.Optional[str]:
        raise NotImplementedError("get_matrix_id must be implemented")

    def _get_logger(self) -> commons_logging.BotLogger:
        return commons_logging.get_logger(f"{self.get_evaluator_class().get_name()}Operator")

    def _get_tentacle_config(self, param_by_name: dict[str, typing.Any]) -> dict:
        evaluator_class = self.get_evaluator_class()
        tentacle_config = dict(self.get_config().get(evaluator_class.get_name(), {}))
        for param_name, param_value in param_by_name.items():
            if param_name in {
                SYMBOLS_PARAM,
                TIME_FRAMES_PARAM,
                CRYPTOCURRENCY_PARAM,
                INCLUDE_IN_CONSTRUCTION_CANDLE_PARAM,
                self.DYNAMIC_DEPENDENCIES_KEY,
                dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY,
            }:
                continue
            tentacle_config[param_name] = param_value
        return tentacle_config

    def _get_symbols_param(self, param_by_name: dict[str, typing.Any]) -> list[str]:
        symbols_value = param_by_name.get(SYMBOLS_PARAM)
        if symbols_value is None:
            return []
        if not isinstance(symbols_value, list):
            raise commons_errors.DSLInterpreterError(
                f"{SYMBOLS_PARAM} must be a list, got {type(symbols_value).__name__}"
            )
        return [str(symbol) for symbol in symbols_value]

    def _get_time_frames_param(self, param_by_name: dict[str, typing.Any]) -> list[str]:
        time_frames_value = param_by_name.get(TIME_FRAMES_PARAM)
        if time_frames_value is None:
            return []
        if not isinstance(time_frames_value, list):
            raise commons_errors.DSLInterpreterError(
                f"{TIME_FRAMES_PARAM} must be a list, got {type(time_frames_value).__name__}"
            )
        return [
            _normalize_time_frame_value(time_frame)
            for time_frame in time_frames_value
        ]

    async def _create_evaluator_instance(
        self,
        evaluator_class: type,
        tentacle_config: dict,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        matrix_id: str,
        symbol: typing.Optional[str],
        time_frame: typing.Optional[str],
        cryptocurrency: typing.Optional[str],
    ):
        await _ensure_dsl_bot_storage_registered()
        evaluator_instance = await evaluator_factory.create_dsl_evaluator(
            evaluator_class,
            _get_local_tentacles_setup_config(),
            matrix_id,
            exchange_manager.exchange_name,
            tentacle_config,
            DSL_BOT_ID,
            symbol=symbol,
            time_frame=time_frame,
            cryptocurrency=cryptocurrency,
        )
        if evaluator_instance is None:
            raise commons_errors.DSLInterpreterError(
                f"Failed to create evaluator {evaluator_class.get_name()}"
            )
        return evaluator_instance

    def _init_strategy_time_frames(
        self,
        evaluator_instance,
        tentacle_config: dict,
    ) -> None:
        evaluator_instance.strategy_time_frames = evaluators.StrategyEvaluator.get_required_time_frames(
            self.get_config(),
            _get_local_tentacles_setup_config(),
            strategy_config=tentacle_config,
        )

    async def _execute_ta_evaluator_via_ohlcv(
        self,
        evaluator_instance,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        matrix_id: str,
        symbol: str,
        time_frame: str,
        cryptocurrency: typing.Optional[str],
        include_in_construction_candle: bool = False,
    ) -> typing.Any:
        import octobot_trading.api as trading_api

        time_frame_value = _normalize_time_frame_value(time_frame)
        exchange_name = exchange_manager.exchange_name
        exchange_id = trading_api.get_exchange_id_from_matrix_id(exchange_name, matrix_id)
        symbol_data = evaluator_instance.get_exchange_symbol_data(exchange_name, exchange_id, symbol)
        if symbol_data is None:
            raise commons_errors.DSLInterpreterError(
                f"Missing symbol data for {symbol} on {exchange_name}"
            )
        if not trading_api.are_symbol_candles_initialized(
            exchange_manager, symbol, time_frame_value
        ):
            raise commons_errors.DSLInterpreterError(
                f"Missing OHLCV data for {symbol} {time_frame_value} on {exchange_name}"
            )
        candles_arrays = trading_api.get_symbol_historical_candles(
            symbol_data, time_frame_value, limit=1
        )
        close_candles = candles_arrays[common_enums.PriceIndexes.IND_PRICE_CLOSE.value]
        if close_candles is None or len(close_candles) == 0:
            raise commons_errors.DSLInterpreterError(
                f"Missing OHLCV data for {symbol} {time_frame_value} on {exchange_name}"
            )
        last_candle = trading_api.get_candle_as_list(candles_arrays, 0)
        await evaluator_instance.ohlcv_callback(
            exchange_name,
            exchange_id,
            cryptocurrency,
            symbol,
            time_frame_value,
            last_candle,
            include_in_construction_candle,
        )
        return evaluator_instance.eval_note

    def _get_strategy_symbols_from_dynamic_dependencies(
        self,
        param_by_name: dict[str, typing.Any],
    ) -> list[str]:
        symbols = []
        for dynamic_dependency in self.get_dynamic_dependencies(param_by_name):
            symbol = EvaluatorResult.from_dict(dynamic_dependency.result).symbol
            if symbol:
                symbols.append(symbol)
        return list_util.deduplicate(symbols)

    async def _execute_strategy_evaluator(
        self,
        evaluator_instance,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        matrix_id: str,
        symbol: str,
        time_frame: str,
        cryptocurrency: typing.Optional[str],
    ) -> typing.Any:
        exchange_name = exchange_manager.exchange_name
        await evaluator_instance.matrix_callback(
            matrix_id,
            evaluator_instance.get_name(),
            evaluators_enums.EvaluatorMatrixTypes.TA.value,
            common_constants.START_PENDING_EVAL_NOTE,
            evaluators_constants.EVALUATOR_EVAL_DEFAULT_TYPE,
            None,
            None,
            exchange_name,
            cryptocurrency,
            symbol,
            time_frame,
        )
        return evaluator_instance.eval_note

    def _build_evaluator_result(
        self,
        evaluator_instance,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        matrix_id: str,
        symbol: typing.Optional[str],
        time_frame: typing.Optional[str],
        cryptocurrency: typing.Optional[str],
        eval_note: typing.Any,
    ) -> dict:
        evaluator_type = evaluator_instance.evaluator_type
        matrix_manager.set_tentacle_value(
            matrix_id,
            matrix_manager.get_matrix_default_value_path(
                evaluator_instance.get_name(),
                evaluator_type.value,
                exchange_name=exchange_manager.exchange_name,
                cryptocurrency=cryptocurrency,
                symbol=symbol,
                time_frame=time_frame,
            ),
            evaluator_type.value,
            eval_note,
        )
        return EvaluatorResult(
            eval_note=eval_note,
            symbol=symbol,
            time_frame=time_frame,
            evaluator_name=evaluator_instance.get_name(),
            evaluator_type=evaluator_type.value,
            cryptocurrency=cryptocurrency,
        ).to_dict(include_default_values=False)

    async def _execute_evaluator_for_context(
        self,
        evaluator_instance,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        matrix_id: str,
        symbol: str,
        time_frame: str,
        cryptocurrency: typing.Optional[str],
        param_by_name: dict[str, typing.Any],
        tentacle_config: dict,
    ) -> dict:
        with evaluator_instance.disabled_evaluation_push():
            if isinstance(evaluator_instance, evaluators.TAEvaluator):
                include_in_construction_candle = bool(
                    param_by_name.get(INCLUDE_IN_CONSTRUCTION_CANDLE_PARAM, False)
                )
                eval_note = await self._execute_ta_evaluator_via_ohlcv(
                    evaluator_instance,
                    exchange_manager,
                    matrix_id,
                    symbol,
                    time_frame,
                    cryptocurrency,
                    include_in_construction_candle=include_in_construction_candle,
                )
            elif isinstance(evaluator_instance, evaluators.StrategyEvaluator):
                self._init_strategy_time_frames(evaluator_instance, tentacle_config)
                eval_note = await self._execute_strategy_evaluator(
                    evaluator_instance,
                    exchange_manager,
                    matrix_id,
                    symbol,
                    time_frame,
                    cryptocurrency,
                )
            else:
                raise commons_errors.DSLInterpreterError(
                    f"Evaluator {evaluator_instance.get_name()} has no supported DSL execution path"
                )
        evaluator_result = self._build_evaluator_result(
            evaluator_instance,
            exchange_manager,
            matrix_id,
            symbol,
            time_frame,
            cryptocurrency,
            eval_note,
        )
        self._get_logger().info(
            f"Evaluator {evaluator_instance.get_name()} result for {symbol} {time_frame}: {evaluator_result}"
        )
        return evaluator_result

    async def _execute_evaluator_for_symbol_and_time_frame(
        self,
        evaluator_class: type,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        matrix_id: str,
        symbol: str,
        time_frame: str,
        cryptocurrency_override: typing.Optional[str],
        param_by_name: dict[str, typing.Any],
        tentacle_config: dict,
    ) -> dict:
        cryptocurrency = _get_cryptocurrency_from_symbol(symbol, cryptocurrency_override)
        evaluator_instance = await self._create_evaluator_instance(
            evaluator_class,
            tentacle_config,
            exchange_manager,
            matrix_id,
            symbol,
            time_frame,
            cryptocurrency,
        )
        return await self._execute_evaluator_for_context(
            evaluator_instance,
            exchange_manager,
            matrix_id,
            symbol,
            time_frame,
            cryptocurrency,
            param_by_name,
            tentacle_config,
        )

    async def _execute_strategy_evaluators(
        self,
        evaluator_class: type,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        matrix_id: str,
        symbols: list[str],
        primary_time_frame: str,
        cryptocurrency_override: typing.Optional[str],
        param_by_name: dict[str, typing.Any],
        tentacle_config: dict,
    ) -> list[dict]:
        evaluator_results = []
        for symbol in symbols:
            evaluator_results.append(
                await self._execute_evaluator_for_symbol_and_time_frame(
                    evaluator_class,
                    exchange_manager,
                    matrix_id,
                    symbol,
                    primary_time_frame,
                    cryptocurrency_override,
                    param_by_name,
                    tentacle_config,
                )
            )
        return evaluator_results

    async def _execute_evaluators_per_symbol_and_time_frame(
        self,
        evaluator_class: type,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        matrix_id: str,
        symbols: list[str],
        time_frames: list[str],
        cryptocurrency_override: typing.Optional[str],
        param_by_name: dict[str, typing.Any],
        tentacle_config: dict,
    ) -> list[dict]:
        evaluator_results = []
        for symbol in symbols:
            for time_frame in time_frames:
                evaluator_results.append(
                    await self._execute_evaluator_for_symbol_and_time_frame(
                        evaluator_class,
                        exchange_manager,
                        matrix_id,
                        symbol,
                        time_frame,
                        cryptocurrency_override,
                        param_by_name,
                        tentacle_config,
                    )
                )
        return evaluator_results

    async def _execute_evaluator(
        self,
        evaluator_class: type,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        matrix_id: str,
        symbols: list[str],
        time_frames: list[str],
        cryptocurrency_override: typing.Optional[str],
        param_by_name: dict[str, typing.Any],
        tentacle_config: dict,
    ) -> list[dict]:
        if not time_frames:
            raise commons_errors.DSLInterpreterError(
                f"Evaluator {evaluator_class.get_name()} requires time_frames parameter"
            )
        if issubclass(evaluator_class, evaluators.StrategyEvaluator):
            if not symbols:
                raise commons_errors.DSLInterpreterError(
                    f"Evaluator {evaluator_class.get_name()} requires symbols from dynamic dependencies"
                )
            return await self._execute_strategy_evaluators(
                evaluator_class,
                exchange_manager,
                matrix_id,
                symbols,
                time_frames[0],
                cryptocurrency_override,
                param_by_name,
                tentacle_config,
            )
        if not symbols:
            raise commons_errors.DSLInterpreterError(
                f"Evaluator {evaluator_class.get_name()} requires symbols parameter"
            )
        return await self._execute_evaluators_per_symbol_and_time_frame(
            evaluator_class,
            exchange_manager,
            matrix_id,
            symbols,
            time_frames,
            cryptocurrency_override,
            param_by_name,
            tentacle_config,
        )

    async def pre_compute(self) -> None:
        await super().pre_compute()
        exchange_manager = self.get_exchange_manager()
        matrix_id = self.get_matrix_id()
        if exchange_manager is None:
            raise commons_errors.DSLInterpreterError(
                "Exchange manager is required to execute evaluator operator"
            )
        if matrix_id is None:
            raise commons_errors.DSLInterpreterError(
                "Matrix id is required to execute evaluator operator"
            )
        param_by_name = self.get_computed_value_by_parameter()
        evaluator_class = self.get_evaluator_class()
        time_frames = self._get_time_frames_param(param_by_name)
        cryptocurrency_override = param_by_name.get(CRYPTOCURRENCY_PARAM)
        if issubclass(evaluator_class, evaluators.StrategyEvaluator):
            symbols = self._get_strategy_symbols_from_dynamic_dependencies(param_by_name)
        else:
            symbols = self._get_symbols_param(param_by_name)
            if cryptocurrency_override is not None and len(symbols) > 1:
                raise commons_errors.DSLInterpreterError(
                    "Cryptocurrency override is only valid for a single symbol"
                )
        for dynamic_dependency in self.get_dynamic_dependencies(param_by_name):
            _seed_matrix_from_injected_evaluator_result(
                matrix_id,
                exchange_manager.exchange_name,
                EvaluatorResult.from_dict(dynamic_dependency.result),
            )
        tentacle_config = self._get_tentacle_config(param_by_name)
        self.value = await self._execute_evaluator(
            evaluator_class,
            exchange_manager,
            matrix_id,
            symbols,
            time_frames,
            cryptocurrency_override,
            param_by_name,
            tentacle_config,
        )

    def get_dependencies(self) -> typing.List[dsl_interpreter.InterpreterDependency]:
        import octobot_trading.dsl as trading_dsl

        evaluator_class = self.get_evaluator_class()
        param_by_name = self.get_computed_value_by_parameter()
        local_dependencies = evaluator_class.get_dsl_dependencies(
            param_by_name, self.get_config(), None
        )
        symbols_from_dynamic_dependencies = self._get_strategy_symbols_from_dynamic_dependencies(
            param_by_name
        )
        if issubclass(evaluator_class, evaluators.StrategyEvaluator):
            symbols = symbols_from_dynamic_dependencies
        else:
            symbols = list_util.deduplicate(
                self._get_symbols_param(param_by_name) + symbols_from_dynamic_dependencies
            )
        time_frames = self._get_time_frames_param(param_by_name)
        if time_frames:
            for symbol in symbols:
                for time_frame in time_frames:
                    local_dependencies.append(
                        trading_dsl.SymbolDependency(symbol=symbol, time_frame=time_frame)
                    )
        else:
            for symbol in symbols:
                local_dependencies.append(trading_dsl.SymbolDependency(symbol=symbol))
        return super().get_dependencies() + local_dependencies


def create_evaluator_operator(
    evaluator_class: type,
    exchange_manager: typing.Optional["octobot_trading.exchanges.ExchangeManager"],
    config: dict,
    matrix_id: typing.Optional[str],
) -> type:
    """
    Create a DSL operator class that, when called, instantiates and executes
    the given evaluator.
    :param evaluator_class: The evaluator class to execute
    :param exchange_manager: The exchange manager to use for evaluator execution
    :param config: The configuration to use for evaluator execution
    :param matrix_id: The matrix id to use for evaluator execution
    :return: A DSL operator class for registration with an Interpreter
    """
    _operator_parameters: list[dsl_interpreter.OperatorParameter] = []
    operator_name = str_util.camel_to_snake(evaluator_class.get_name())
    class _ContextProviderMixin:
        def get_exchange_manager(
            self,
        ) -> typing.Optional["octobot_trading.exchanges.ExchangeManager"]:
            return exchange_manager

        def get_evaluator_class(self) -> type:
            return evaluator_class

        def get_config(self) -> dict:
            return config

        def get_matrix_id(self) -> typing.Optional[str]:
            return matrix_id

    class _EvaluatorOperatorImpl(_ContextProviderMixin, EvaluatorOperator):
        DESCRIPTION = f"Executes the {evaluator_class.get_name()} evaluator"
        EXAMPLE = f"{operator_name}()"

        @staticmethod
        def get_name() -> str:
            return operator_name

        @classmethod
        def get_evaluator_meta_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            meta_parameters = [
                dsl_interpreter.OperatorParameter(
                    name=TIME_FRAMES_PARAM,
                    description="Evaluated time frames",
                    required=False,
                    type=list,
                    default=None,
                ),
            ]
            if not issubclass(evaluator_class, evaluators.StrategyEvaluator):
                meta_parameters.extend([
                    dsl_interpreter.OperatorParameter(
                        name=SYMBOLS_PARAM,
                        description="Evaluated trading symbols",
                        required=False,
                        type=list,
                        default=None,
                    ),
                    dsl_interpreter.OperatorParameter(
                        name=CRYPTOCURRENCY_PARAM,
                        description="Evaluated cryptocurrency",
                        required=False,
                        type=str,
                        default=None,
                    ),
                ])
            if issubclass(evaluator_class, evaluators.TAEvaluator):
                meta_parameters.append(
                    dsl_interpreter.OperatorParameter(
                        name=INCLUDE_IN_CONSTRUCTION_CANDLE_PARAM,
                        description="Include the in-construction candle when executing the TA evaluator",
                        required=False,
                        type=bool,
                        default=False,
                    )
                )
            return meta_parameters

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            if not _operator_parameters:
                _operator_parameters.extend(_create_evaluator_operator_parameters(
                    evaluator_class, config
                ))
            return (
                _operator_parameters
                + cls.get_evaluator_meta_parameters()
                + cls.get_dynamic_dependencies_parameters()
                + cls.get_re_callable_parameters()
            )

    return _EvaluatorOperatorImpl


def create_all_evaluator_operators(
    exchange_manager: typing.Optional["octobot_trading.exchanges.ExchangeManager"],
    config: dict,
    matrix_id: typing.Optional[str],
) -> list[type]:
    """
    Create DSL operators for all available evaluators.
    :param exchange_manager: The exchange manager to use for evaluator execution
    :param config: The configuration to use for evaluator execution
    :param matrix_id: The matrix id to use for evaluator execution
    :return: List of DSL operator classes for registration with an Interpreter
    """

    operators = []
    for evaluator_class in tentacles_management.get_all_classes_from_parent(
        evaluators.AbstractEvaluator
    ):
        operators.append(
            create_evaluator_operator(
                evaluator_class, exchange_manager, config, matrix_id
            )
        )
    return operators
