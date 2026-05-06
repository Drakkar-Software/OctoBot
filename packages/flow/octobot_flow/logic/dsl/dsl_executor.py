import typing
import contextlib

import octobot_commons.dsl_interpreter
import octobot_commons.signals
import octobot_commons.errors
import octobot_commons.profiles
import octobot_commons.logging
import octobot_trading.exchanges
import octobot_trading.dsl
import octobot_trading.modes as trading_modes

import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.enums

# avoid circular import
from octobot_flow.logic.dsl.dsl_action_execution_context import dsl_action_execution
from octobot_flow.logic.actions.abstract_action_executor import AbstractActionExecutor

import tentacles.Meta.DSL_operators as dsl_operators
import tentacles.Meta.DSL_operators.octobot_process_operators.octobot_process_ops as octobot_process_ops



class DSLExecutor(AbstractActionExecutor):
    def __init__(
        self,
        profile_data: octobot_commons.profiles.ProfileData,
        exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
        dsl_script: typing.Optional[str],
        dependencies: typing.Optional[octobot_commons.signals.SignalDependencies] = None,
    ):
        super().__init__()
        self._exchange_manager = exchange_manager
        self._dependencies = dependencies
        self._dependencies_config: dict = profile_data.to_profile("").config
        self._interpreter_signals: octobot_commons.dsl_interpreter.OperatorSignals = None # type: ignore (reset when interpreter is created)
        self._interpreter: octobot_commons.dsl_interpreter.Interpreter = self._create_interpreter(None)
        if dsl_script:
            self._interpreter.prepare(dsl_script)

    def get_flow_operator_classes(
        self,
    ) -> list[typing.Type[octobot_commons.dsl_interpreter.Operator]]:
        return (
            octobot_commons.dsl_interpreter.get_all_operators()
            + dsl_operators.create_ohlcv_operators(self._exchange_manager, None, None)
            + dsl_operators.create_portfolio_operators(self._exchange_manager)
            + dsl_operators.create_create_order_operators(
                self._exchange_manager, trading_mode=None, dependencies=self._dependencies
            )
            + dsl_operators.create_cancel_order_operators(
                self._exchange_manager, trading_mode=None, dependencies=self._dependencies
            )
            + dsl_operators.create_fetch_order_operators(self._exchange_manager)
            + dsl_operators.create_blockchain_wallet_operators(self._exchange_manager)
            + trading_modes.create_all_trading_mode_operators(
                self._exchange_manager, self._dependencies_config
            )
            + dsl_operators.create_copy_exchange_account_operators(
                copier_exchange_manager=self._exchange_manager,
                copier_trading_mode=None,
            )
            + octobot_process_ops.create_octobot_process_operators(
                self._interpreter_signals
            )
        ) # type: ignore (list[type[Operator]])

    def _create_interpreter(
        self, previous_execution_result: typing.Optional[dict]
    ) -> octobot_commons.dsl_interpreter.Interpreter:
        self._interpreter_signals = octobot_commons.dsl_interpreter.OperatorSignals()
        return octobot_commons.dsl_interpreter.Interpreter(
            self.get_flow_operator_classes()
        )

    def get_dependencies(self) -> list[
        octobot_commons.dsl_interpreter.InterpreterDependency
    ]:
        return self._interpreter.get_dependencies()

    def get_top_operator(self) -> typing.Union[
        octobot_commons.dsl_interpreter.Operator,
        octobot_commons.dsl_interpreter.ComputedOperatorParameterType,
    ]:
        return self._interpreter.get_top_operator()

    @dsl_action_execution
    async def execute_action(
        self,
        action: octobot_flow.entities.DSLScriptActionDetails,
        *,
        operator_signals: typing.Optional[
            list[tuple[
                typing.Type[octobot_commons.dsl_interpreter.SignalableOperatorMixin],
                str
            ]]
        ] = None,
    ) -> octobot_commons.dsl_interpreter.DSLCallResult:
        self._interpreter = self._create_interpreter(
            action.previous_execution_result
        )
        expression = action.get_resolved_dsl_script()
        try:
            if operator_signals:
                signals_update = {
                    operator_class.get_name(): signal # type: ignore
                    for operator_class, signal in operator_signals
                }
                self._logger().info(f"Executing action with operator signals: {signals_update}")
            else:
                signals_update = {}
            self._interpreter_signals.sync(signals_update)
            interpretation = await self._interpreter.interprete(expression)
            return octobot_commons.dsl_interpreter.DSLCallResult(
                statement=expression,
                result=interpretation,
            )
        except octobot_commons.errors.MaxAttemptsExceededError as err:
            self._logger().error(f"Max attempts exceeded: {err}")
            return octobot_commons.dsl_interpreter.DSLCallResult(
                statement=expression,
                error=octobot_flow.enums.ActionErrorStatus.MAX_ATTEMPTS_EXCEEDED.value
            )
        except octobot_commons.errors.ErrorStatementEncountered as err:
            self._logger().exception(
                err, True, f"Generic DSL error statement encountered: {err}"
            )
            validated_error = (
                err.args[0] if err.args and err.args[0] in octobot_flow.enums.ActionErrorStatus 
                else octobot_flow.enums.ActionErrorStatus.DSL_EXECUTION_ERROR.value
            )
            return octobot_commons.dsl_interpreter.DSLCallResult(
                statement=expression,
                error=validated_error
            )

    @contextlib.asynccontextmanager
    async def dependencies_context(
        self, actions: list[octobot_flow.entities.AbstractActionDetails]
    ) -> typing.AsyncGenerator[None, None]:
        try:
            all_dependencies = self._get_all_dependencies(actions) if actions else []
            # 1. validate static dependencies
            self._validate_dependencies(all_dependencies)
            # 2. instanciate dynamic dependencies
            # todo initialize dynamic dependencies when implemented
            yield
        finally:
            # todo clean up dynamic dependencies when required
            pass

    def _validate_dependencies(self, dependencies: list[octobot_commons.dsl_interpreter.InterpreterDependency]):
        if any(
            isinstance(dependency, octobot_trading.dsl.SymbolDependency) for dependency in dependencies
        ) and not self._exchange_manager:
            raise octobot_flow.errors.MissingDSLExecutorDependencyError(
                "Exchange manager is required when using symbol dependencies"
            )

    def _get_all_dependencies(
        self, actions: list[octobot_flow.entities.AbstractActionDetails]
    ) -> list[octobot_commons.dsl_interpreter.InterpreterDependency]:
        dependencies = []
        for action in actions:
            if isinstance(action, octobot_flow.entities.DSLScriptActionDetails):
                dsl_script = action.get_resolved_dsl_script()
                self._interpreter.prepare(dsl_script)
                dependencies.extend(self._interpreter.get_dependencies())
        return dependencies

    @classmethod
    def _logger(cls) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(cls.__name__)
