import typing
import contextlib

import octobot_commons.dsl_interpreter
import octobot_commons.signals
import octobot_commons.errors
import octobot_trading.exchanges
import octobot_trading.dsl

import tentacles.Meta.DSL_operators as dsl_operators

import octobot_flow.entities
import octobot_flow.errors

# avoid circular import
from octobot_flow.logic.dsl.dsl_action_execution_context import dsl_action_execution
from octobot_flow.logic.actions.abstract_action_executor import AbstractActionExecutor



class DSLExecutor(AbstractActionExecutor):
    def __init__(
        self, 
        exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
        dsl_script: typing.Optional[str], 
        dependencies: typing.Optional[octobot_commons.signals.SignalDependencies] = None,
    ):
        super().__init__()

        self._exchange_manager = exchange_manager
        self._dependencies = dependencies
        self._interpreter: octobot_commons.dsl_interpreter.Interpreter = self._create_interpreter(None)
        if dsl_script:
            self._interpreter.prepare(dsl_script)

    def _create_interpreter(
        self, previous_execution_result: typing.Optional[dict]
    ):
        return octobot_commons.dsl_interpreter.Interpreter(
            octobot_commons.dsl_interpreter.get_all_operators()
            + dsl_operators.create_ohlcv_operators(self._exchange_manager, None, None)
            + dsl_operators.create_portfolio_operators(self._exchange_manager)
            + dsl_operators.create_create_order_operators(
                self._exchange_manager, trading_mode=None, dependencies=self._dependencies
            )
            + dsl_operators.create_cancel_order_operators(
                self._exchange_manager, trading_mode=None, dependencies=self._dependencies
            )
            + dsl_operators.create_blockchain_wallet_operators(self._exchange_manager)
        )

    def get_dependencies(self) -> list[
        octobot_commons.dsl_interpreter.InterpreterDependency
    ]:
        return self._interpreter.get_dependencies()

    @dsl_action_execution
    async def execute_action(self, action: octobot_flow.entities.DSLScriptActionDetails) -> typing.Any:
        self._interpreter = self._create_interpreter(
            action.previous_execution_result
        )
        expression = action.get_resolved_dsl_script()
        try:
            return octobot_commons.dsl_interpreter.DSLCallResult(
                statement=expression,
                result=await self._interpreter.interprete(expression),
            )
        except octobot_commons.errors.ErrorStatementEncountered as err:
            return octobot_commons.dsl_interpreter.DSLCallResult(
                statement=expression,
                error=err.args[0] if err.args else ""
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
