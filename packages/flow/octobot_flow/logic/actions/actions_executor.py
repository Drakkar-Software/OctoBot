import typing

import octobot_commons.logging
import octobot_commons.profiles
import octobot_commons.dsl_interpreter
import octobot_trading.exchanges

import octobot.community

import octobot_flow.entities
import octobot_flow.repositories.community
import octobot_flow.logic.dsl
import octobot_flow.enums as octobot_flow_enums_import
import octobot_flow.errors

import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators
import tentacles.Meta.DSL_operators.blockchain_wallet_operators as blockchain_wallet_operators


class ActionsExecutor:
    def __init__(
        self,
        maybe_community_repository: typing.Optional[octobot_flow.repositories.community.CommunityRepository],
        exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
        profile_data: octobot_commons.profiles.ProfileData,
        automation: octobot_flow.entities.AutomationDetails,
        actions: list[octobot_flow.entities.AbstractActionDetails],
        update_execution_details: bool,
    ):
        self.changed_elements: list[octobot_flow_enums_import.ChangedElements] = []
        self.next_execution_scheduled_to: float = 0

        self._maybe_community_repository: typing.Optional[
            octobot_flow.repositories.community.CommunityRepository
        ] = maybe_community_repository
        self._exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager] = exchange_manager
        self._profile_data: octobot_commons.profiles.ProfileData = profile_data
        self._automation: octobot_flow.entities.AutomationDetails = automation
        self._actions: list[octobot_flow.entities.AbstractActionDetails] = actions
        self._update_execution_details: bool = update_execution_details

    async def execute(self):
        dsl_executor = octobot_flow.logic.dsl.DSLExecutor(
            self._profile_data,
            self._exchange_manager,
            None,
        )
        if self._exchange_manager:
            await octobot_trading.exchanges.create_exchange_channels(self._exchange_manager)
        recall_dag_details: typing.Optional[octobot_commons.dsl_interpreter.ReCallingOperatorResult] = None
        synchronized_exchange_account_elements: list[octobot_flow.entities.ExchangeAccountElements] = []
        async with dsl_executor.dependencies_context(self._actions):
            for index, action in enumerate(self._actions):
                await self._execute_action(dsl_executor, action)
                if self._update_execution_details:
                    recall_dag_details, should_stop_processing = await self._handle_execution_result(
                        dsl_executor, action, index, synchronized_exchange_account_elements
                    )
                    if should_stop_processing:
                        break
        self._sync_after_execution(synchronized_exchange_account_elements)
        if self._update_execution_details:
            await self._update_actions_history()
        await self._insert_execution_bot_logs(dsl_executor.pending_bot_logs)
        if recall_dag_details:
            self._reset_dag_to(recall_dag_details)
            # next execution is scheduled to the time configured by the reset operator
            self.next_execution_scheduled_to = self._compute_next_execution_scheduled_to(
                recall_dag_details
            )
        elif self._update_execution_details:
            # no reset: schedule immediately
            self.next_execution_scheduled_to = 0

    async def _handle_execution_result(
        self,
        dsl_executor: "octobot_flow.logic.dsl.DSLExecutor",
        action: octobot_flow.entities.AbstractActionDetails,
        index: int,
        synchronized_exchange_account_elements: list[octobot_flow.entities.ExchangeAccountElements],
    ) -> tuple[typing.Optional[octobot_commons.dsl_interpreter.ReCallingOperatorResult], bool]:
        if not isinstance(action.result, dict):
            return None, False
        if post_iteration_actions_details := self._get_post_iteration_details(action.result):
            if early_return := await self._execute_post_iteration_actions(
                dsl_executor,
                post_iteration_actions_details,
                synchronized_exchange_account_elements,
            ):
                return early_return
        return self._create_recall_dag_details_if_necessary(
            action.id, action.result, index, self._actions
        )

    def _get_post_iteration_details(
        self,
        action_result: dict,
    ) -> typing.Optional[octobot_flow.entities.PostIterationActionsDetails]:
        """
        If ``PostIterationActionsDetails`` is present on ``action_result`` or inside the recall
        wrapper's ``last_execution_result``, return the dict that contains that key; else None.
        """
        post_iter_name = octobot_flow.entities.PostIterationActionsDetails.__name__
        post_iteration_source: typing.Optional[dict] = None
        if post_iter_name in action_result:
            post_iteration_source = action_result
        elif octobot_commons.dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(
            action_result
        ):
            recall_wrapper = octobot_commons.dsl_interpreter.ReCallingOperatorResult.from_dict(
                action_result[octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__]
            )
            inner_last = recall_wrapper.last_execution_result
            if isinstance(inner_last, dict) and post_iter_name in inner_last:
                post_iteration_source = inner_last
        return octobot_flow.entities.PostIterationActionsDetails.from_dict(
            post_iteration_source[post_iter_name]
        ) if post_iteration_source else None

    async def _execute_post_iteration_actions(
        self,
        dsl_executor: "octobot_flow.logic.dsl.DSLExecutor",
        post_iteration_actions_details: octobot_flow.entities.PostIterationActionsDetails,
        synchronized_exchange_account_elements: list[octobot_flow.entities.ExchangeAccountElements],
    ) -> typing.Optional[
        tuple[
            typing.Optional[octobot_commons.dsl_interpreter.ReCallingOperatorResult],
            bool,
        ]
    ]:
        if post_iteration_actions_details.stop_automation:
            self._get_logger().info(f"Stopping automation: {self._automation.metadata.automation_id}")
            self._automation.post_actions.stop_automation = True
            # todo cancel open orders and sell assets if required in action config
            await self._await_recallable_operator_signal(
                dsl_executor,
                octobot_commons.dsl_interpreter.OperatorSignal.STOP.value,
            )
            return None, True
        if post_iteration_actions_details.configuration_update is not None:
            if not post_iteration_actions_details.configuration_update:
                raise octobot_flow.errors.AutomationActionError(
                    "configuration_update must be a non-empty DSL string."
                )
            self._get_logger().info(
                "Automation configuration update requested for automation: %s",
                self._automation.metadata.automation_id,
            )
            executable_actions = self._automation.actions_dag.get_executable_actions()
            if len(executable_actions) != 1:
                raise octobot_flow.errors.AutomationActionError(
                    "update_automation_configuration requires exactly one executable DAG action; "
                    f"found {len(executable_actions)}: {[a.id for a in executable_actions]}"
                )
            target_action = executable_actions[0]
            if not isinstance(target_action, octobot_flow.entities.DSLScriptActionDetails):
                raise octobot_flow.errors.AutomationActionError(
                    "update_automation_configuration requires a DSL script action; "
                    f"got {type(target_action).__name__} for action {target_action.id!r}."
                )
            target_action.dsl_script = post_iteration_actions_details.configuration_update
            executed_dag_action, dag_action_result, dag_action_index = await self._await_recallable_operator_signal(
                dsl_executor,
                octobot_commons.dsl_interpreter.OperatorSignal.UPDATE_CONFIG.value,
            )
            if executed_dag_action is None or dag_action_result is None:
                raise octobot_flow.errors.AutomationActionError(
                    "update_automation_configuration did not receive a result from the signaled DAG action."
                )
            if not dag_action_result.succeeded():
                raise octobot_flow.errors.AutomationActionError(
                    f"update_automation_configuration failed: {dag_action_result.error}"
                )
            return self._create_recall_dag_details_if_necessary(
                executed_dag_action.id,
                dag_action_result.result,
                dag_action_index,
                self._automation.actions_dag.actions,
            )
        if post_iteration_actions_details.updated_exchange_account_elements is not None:
            synchronized_exchange_account_elements.append(
                octobot_flow.entities.ExchangeAccountElements.from_dict(
                    post_iteration_actions_details.updated_exchange_account_elements
                )
            )
            # return via the default path, build recall DAG details if necessary
        return None

    def _create_recall_dag_details_if_necessary(
        self,
        action_id: str,
        action_result: typing.Optional[typing.Any],
        action_index: int,
        actions: list[octobot_flow.entities.AbstractActionDetails],
    ) -> tuple[typing.Optional[octobot_commons.dsl_interpreter.ReCallingOperatorResult], bool]:
        """
        Create recall DAG details if necessary.
        returns:
        - recall_dag_details: the recall DAG details if necessary (or None)
        - reset_to_other_action: True if the reset to other action is necessary, False otherwise
        """
        if not octobot_commons.dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(action_result):
            return None, False
        recall_dag_details = octobot_commons.dsl_interpreter.ReCallingOperatorResult.from_dict(
            action_result[octobot_commons.dsl_interpreter.ReCallingOperatorResult.__name__] # type: ignore
        )
        if not recall_dag_details.reset_to_id:
            # reset to the current action if no specific id is provided (loop on this action)
            recall_dag_details.reset_to_id = action_id
        if recall_dag_details.reset_to_id == action_id:
            # Keep executing other selected actions if any: those are not affected by the reset
            # as they don't depend on the reset action
            return recall_dag_details, False
        
        # Reset to a past action: interrupt execution of the following actions 
        # as they might depend on the reset action
        if action_index < len(actions) - 1:
            interrupted_action = actions[action_index + 1:]
            self._get_logger().info(
                f"DAG reset required. Interrupting execution of "
                f"{len(interrupted_action)} actions: "
                f"{', '.join([action.id for action in interrupted_action])}"
            )
        return recall_dag_details, True

    @staticmethod
    def _re_calling_payload_for_execution_stop(
        action: octobot_flow.entities.DSLScriptActionDetails,
    ) -> typing.Optional[dict]:
        for candidate in (action.previous_execution_result, action.result):
            if not candidate or not isinstance(candidate, dict):
                continue
            if octobot_commons.dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(
                candidate
            ):
                return candidate
        return None

    async def _await_recallable_operator_signal(
        self,
        dsl_executor: "octobot_flow.logic.dsl.DSLExecutor",
        signal: str,
    ) -> tuple[typing.Optional[octobot_flow.entities.DSLScriptActionDetails], typing.Optional[octobot_commons.dsl_interpreter.DSLCallResult], int]:
        self._automation.actions_dag.resolve_dsl_scripts(self._automation.actions_dag.actions)
        operators_by_name: typing.Optional[
            dict[str, typing.Type[octobot_commons.dsl_interpreter.Operator]]
        ] = None
        for index, dag_action in enumerate(self._automation.actions_dag.actions):
            if not isinstance(dag_action, octobot_flow.entities.DSLScriptActionDetails):
                continue
            re_payload = self._re_calling_payload_for_execution_stop(dag_action)
            if re_payload is None or not isinstance(re_payload, dict):
                continue
            try:
                keyword = octobot_commons.dsl_interpreter.ReCallingOperatorResult.get_keyword(
                    re_payload
                )
            except KeyError:
                continue
            if keyword is None:
                continue
            if operators_by_name is None:
                operators_by_name = {
                    operator_class.get_name(): operator_class
                    for operator_class in dsl_executor.get_flow_operator_classes()
                }
            operator_class = operators_by_name.get(keyword)
            if operator_class is None or not issubclass(
                operator_class,
                octobot_commons.dsl_interpreter.SignalableOperatorMixin,
            ):
                continue
            if not operator_class.should_dispatch_operator_signal_for_result(
                signal,
                re_payload,
            ):
                continue
            dag_action_result = await self._execute_signaled_action(
                dsl_executor, dag_action, operator_class, signal
            )
            return dag_action, dag_action_result, index
        return None, None, -1

    async def _execute_action(
        self,
        dsl_executor: "octobot_flow.logic.dsl.DSLExecutor",
        action: octobot_flow.entities.AbstractActionDetails
    ) -> octobot_commons.dsl_interpreter.DSLCallResult:
        if isinstance(action, octobot_flow.entities.DSLScriptActionDetails):
            return await dsl_executor.execute_action(action)
        raise octobot_flow.errors.UnsupportedActionTypeError(
            f"{self.__class__.__name__} does not support action type: {type(action)}"
        ) from None

    async def _execute_signaled_action(
        self,
        dsl_executor: "octobot_flow.logic.dsl.DSLExecutor",
        action: octobot_flow.entities.AbstractActionDetails,
        operator_class: typing.Type[octobot_commons.dsl_interpreter.SignalableOperatorMixin],
        signal: str,
    ) -> octobot_commons.dsl_interpreter.DSLCallResult:
        return await dsl_executor.execute_action(
            action,
            operator_signals=[
                (
                    operator_class,
                    signal,
                ),
            ],
        )

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

    def _sync_after_execution(
        self,
        synchronized_exchange_account_elements: list[octobot_flow.entities.ExchangeAccountElements],
    ):
        if synchronized_exchange_account_elements:
            self._get_logger().info(
                f"Exchange account elements are being updated from {len(synchronized_exchange_account_elements)}"
                f"synchronized exchange account elements on {[s.name for s in synchronized_exchange_account_elements]}"
                f"returned by actions; this iteration does not apply sync_from_exchange_manager from the "
                f"local exchange_manager.",
            )
            if self._automation.exchange_account_elements is None:
                self._automation.exchange_account_elements = octobot_flow.entities.ExchangeAccountElements()
            self.changed_elements = self._automation.exchange_account_elements.merge_synchronized_snapshots(
                synchronized_exchange_account_elements
            )
            return
        if exchange_account_elements := self._automation.exchange_account_elements:
            new_transactions = self._get_new_transactions_from_actions_results(
                exchange_account_elements
            )
            self._sync_exchange_account_elements(exchange_account_elements, new_transactions)

    def _get_new_transactions_from_actions_results(
        self,
        exchange_account_elements: octobot_flow.entities.ExchangeAccountElements,
    ):
        new_transactions = []
        for action in self._actions:
            if not action.is_completed() or not isinstance(action.result, dict):
                continue
            if created_transactions := (
                action.result.get(exchange_operators.CREATED_WITHDRAWALS_KEY, [])
                + action.result.get(blockchain_wallet_operators.CREATED_TRANSACTIONS_KEY, [])
            ):
                new_transactions.extend(created_transactions)
        return new_transactions

    def _sync_exchange_account_elements(
        self,
        exchange_account_elements: octobot_flow.entities.ExchangeAccountElements,
        new_transactions: list[dict],
    ):
        if self._exchange_manager or new_transactions:
            self.changed_elements = exchange_account_elements.sync_from_exchange_manager(
                self._exchange_manager, new_transactions
            )

    def _get_logger(self) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(self.__class__.__name__)
