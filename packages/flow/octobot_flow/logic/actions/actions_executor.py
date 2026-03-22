import typing
import time

import octobot_commons.logging
import octobot_commons.dsl_interpreter
import octobot_trading.exchanges

import octobot.community

import octobot_flow.entities
import octobot_flow.repositories.community
import octobot_flow.logic.dsl
import octobot_flow.enums
import octobot_flow.errors

import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators
import tentacles.Meta.DSL_operators.blockchain_wallet_operators as blockchain_wallet_operators


class ActionsExecutor:
    def __init__(
        self,
        maybe_community_repository: typing.Optional[octobot_flow.repositories.community.CommunityRepository],
        exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
        automation: octobot_flow.entities.AutomationDetails,
        actions: list[octobot_flow.entities.AbstractActionDetails],
        as_reference_account: bool,
    ):
        self.changed_elements: list[octobot_flow.enums.ChangedElements] = []
        self.next_execution_scheduled_to: float = 0

        self._maybe_community_repository: typing.Optional[
            octobot_flow.repositories.community.CommunityRepository
        ] = maybe_community_repository
        self._exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager] = exchange_manager
        self._automation: octobot_flow.entities.AutomationDetails = automation
        self._actions: list[octobot_flow.entities.AbstractActionDetails] = actions
        self._as_reference_account: bool = as_reference_account

    async def execute(self):
        dsl_executor = octobot_flow.logic.dsl.DSLExecutor(
            self._exchange_manager, None
        )
        if self._exchange_manager:
            await octobot_trading.exchanges.create_exchange_channels(self._exchange_manager)
        recall_dag_details: typing.Optional[octobot_commons.dsl_interpreter.ReCallingOperatorResult] = None
        async with dsl_executor.dependencies_context(self._actions):
            for index, action in enumerate(self._actions):
                await self._execute_action(dsl_executor, action)
                recall_dag_details, should_stop_processing = self._handle_execution_result(action, index)
                if should_stop_processing:
                    break
        self._sync_after_execution()
        await self._update_actions_history()
        await self._insert_execution_bot_logs(dsl_executor.pending_bot_logs)
        if recall_dag_details:
            self._reset_dag_to(recall_dag_details)
            # next execution is scheduled to the time configured by the reset operator
            self.next_execution_scheduled_to = self._compute_next_execution_scheduled_to(
                recall_dag_details
            )
        else:
            # no reset: schedule immediately
            self.next_execution_scheduled_to = 0

    def _handle_execution_result(
        self, action: octobot_flow.entities.AbstractActionDetails, index: int
    ) -> tuple[typing.Optional[octobot_commons.dsl_interpreter.ReCallingOperatorResult], bool]:
        if not isinstance(action.result, dict):
            return None, False
        if octobot_flow.entities.PostIterationActionsDetails.__name__ in action.result:
            post_iteration_actions_details = octobot_flow.entities.PostIterationActionsDetails.from_dict(
                action.result[octobot_flow.entities.PostIterationActionsDetails.__name__]
            )
            if post_iteration_actions_details.stop_automation:
                self._get_logger().info(f"Stopping automation: {self._automation.metadata.automation_id}")
                self._automation.post_actions.stop_automation = True
                # todo cancel open orders and sell assets if required in action config
                return None, True
            return None, False
        if octobot_commons.dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(action.result):
            recall_dag_details = octobot_commons.dsl_interpreter.ReCallingOperatorResult.from_dict(
                action.result[octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__]
            )
            if not recall_dag_details.reset_to_id:
                # reset to the current action if no specific id is provided (loop on this action)
                recall_dag_details.reset_to_id = action.id
            if recall_dag_details.reset_to_id == action.id:
                # Keep executing other selected actions if any: those are not affected by the reset
                # as they don't depend on the reset action
                return recall_dag_details, False
            # Reset to a past action: interrupt execution of the following actions 
            # as they might depend on the reset action
            if index < len(self._actions) - 1:
                interrupted_action = self._actions[index + 1: ]
                self._get_logger().info(
                    f"DAG reset required. Interrupting execution of "
                    f"{len(interrupted_action)} actions: "
                    f"{', '.join([action.id for action in interrupted_action])}"
                )
                return recall_dag_details, True
        return None, False

    async def _execute_action(
        self,
        dsl_executor: "octobot_flow.logic.dsl.DSLExecutor",
        action: octobot_flow.entities.AbstractActionDetails
    ):
        if isinstance(action, octobot_flow.entities.DSLScriptActionDetails):
            return await dsl_executor.execute_action(action)
        raise octobot_flow.errors.UnsupportedActionTypeError(
            f"{self.__class__.__name__} does not support action type: {type(action)}"
        ) from None

    def _reset_dag_to(
        self, recall_dag_details: octobot_commons.dsl_interpreter.ReCallingOperatorResult
    ):
        if not recall_dag_details.reset_to_id:
            raise octobot_flow.errors.AutomationDAGResetError(
                f"Reset to id is required to reset the DAG. got: {recall_dag_details}"
            )
        self._automation.actions_dag.reset_to(recall_dag_details.reset_to_id)

    def _compute_next_execution_scheduled_to(
        self, recall_dag_details: octobot_commons.dsl_interpreter.ReCallingOperatorResult
    ) -> float:
        return recall_dag_details.get_next_call_time() or 0

    async def _update_actions_history(self):
        if to_update_actions := [
            action
            for action in self._actions
            if action.should_be_historised_in_database()
        ]:
            raise NotImplementedError("_update_actions_history is not implemented yet")

    async def _insert_execution_bot_logs(self, log_data: list[octobot.community.BotLogData]):
        try:
            community_repository = octobot_flow.repositories.community.ensure_authenticated_community_repository(
                self._maybe_community_repository
            )
            await community_repository.insert_bot_logs(log_data)
        except octobot_flow.errors.CommunityAuthenticationRequiredError:
            # no available community repository: skip bot logs to insert
            self._get_logger().info(
                "No available community repository: bot logs upload is skipped"
            )

    # def _get_or_compute_actions_next_execution_scheduled_to(
    #     self
    # ) -> float: #todo
    #     for action in self._actions:
    #         if action.next_schedule:
    #             next_schedule_details = octobot_flow.entities.NextScheduleParams.from_dict(action.next_schedule)
    #             return next_schedule_details.get_next_schedule_time()
    #     return self._compute_next_execution_scheduled_to(
    #         octobot_flow.constants.DEFAULT_EXTERNAL_TRIGGER_ONLY_NO_ORDER_TIMEFRAME
    #     )

    # def _compute_next_execution_scheduled_to(
    #     self,
    #     time_frame: octobot_commons.enums.TimeFrames
    # ) -> float:
    #     # if this was scheduled, use it as a basis to always start at the same time,
    #     # otherwise use triggered at
    #     current_schedule_time = (
    #         self._automation.execution.current_execution.scheduled_to 
    #         or self._automation.execution.current_execution.triggered_at
    #     )
    #     return current_schedule_time + (
    #         octobot_commons.enums.TimeFramesMinutes[time_frame] * octobot_commons.constants.MINUTE_TO_SECONDS
    #     )

    def _sync_after_execution(self):
        if exchange_account_elements := self._automation.get_exchange_account_elements(
            self._as_reference_account
        ):
            self._sync_automation_from_actions_results(exchange_account_elements)
            self._sync_exchange_account_elements(exchange_account_elements)

    def _sync_automation_from_actions_results(
        self,
        exchange_account_elements: typing.Union[
            octobot_flow.entities.ReferenceExchangeAccountElements,
            octobot_flow.entities.ClientExchangeAccountElements
        ]
    ):
        for action in self._actions:
            if not action.is_completed() or not isinstance(action.result, dict):
                continue
            if created_transactions := (
                action.result.get(exchange_operators.CREATED_WITHDRAWALS_KEY, [])
                + action.result.get(blockchain_wallet_operators.CREATED_TRANSACTIONS_KEY, [])
            ):
                exchange_account_elements.transactions.extend(created_transactions)

    def _sync_exchange_account_elements(
        self, 
        exchange_account_elements: typing.Union[
            octobot_flow.entities.ReferenceExchangeAccountElements,
            octobot_flow.entities.ClientExchangeAccountElements
        ]
    ):
        if self._exchange_manager:
            self.changed_elements = exchange_account_elements.sync_from_exchange_manager(self._exchange_manager)

    def _get_logger(self) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(self.__class__.__name__)
