import contextlib
from octobot_flow.entities.actions.action_details import AbstractActionDetails
import time
import typing

import octobot_commons.logging as common_logging
import octobot.community

import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.errors
import octobot_flow.logic.configuration
import octobot_flow.parsers.sanitizer
import octobot_flow.logic.dsl
import octobot_flow.repositories.community
import octobot_flow.encryption
import octobot_flow.jobs.exchange_account_job as exchange_account_job_import
import octobot_flow.jobs.automation_runner_job as automation_runner_job_import


class AutomationJob:
    """
    Configures the automation environment and runs it:
    1. Parse the automation, initialize if necessary, resolve dependencies and DAG actions to prepare the automation environment. 
    2. Use the AutomationRunner to run the automation itself.
    3. Execute pending priority actions if any, otherwise execute the DAG's executable actions.
    """
    def __init__(
        self,
        automation_state: dict[str, typing.Any],
        added_priority_actions: list[octobot_flow.entities.AbstractActionDetails],
        auth_details: typing.Union[octobot_flow.entities.UserAuthentication, dict],
    ):
        self.automation_state: octobot_flow.entities.AutomationState = (
            octobot_flow.entities.AutomationState.from_dict(automation_state)
        )
        if added_priority_actions:
            # Include added priority actions in the automation state. 
            # All pending priority actions will be executed before any other actions.
            self.automation_state.update_priority_actions(added_priority_actions)
        self._validate_input()
        self.auth_details: octobot_flow.entities.UserAuthentication = octobot_flow.entities.UserAuthentication.from_dict(auth_details) if isinstance(auth_details, dict) else auth_details
        self.is_initialization_run = self._requires_initialization_run()
        self.fetched_actions: list[octobot_flow.entities.AbstractActionDetails] = []
        self._logger: common_logging.BotLogger = common_logging.get_logger(self.__class__.__name__)

    async def run(self) -> list[octobot_flow.entities.AbstractActionDetails]:
        if self.is_initialization_run:
            # Configure the automation
            return await self.execute_initialization_run()
        t0 = time.time()
        executed_actions = []
        async with self._maybe_authenticator() as maybe_authenticator:
            maybe_community_repository = (
                octobot_flow.repositories.community.CommunityRepository(maybe_authenticator)
                if maybe_authenticator else None
            )
            with octobot_flow.encryption.decrypted_bots_configurations(self.automation_state):
                to_execute_actions, are_priority_actions = self._get_actions_to_execute()
                if are_priority_actions:
                    self._logger.info(f"Running {len(to_execute_actions)} priority actions: {to_execute_actions}")
                    self._resolve_dsl_scripts(to_execute_actions, True)
                else:
                    # fetch the actions and signals if any
                    await self._fetch_actions(maybe_authenticator)
                    # resolve the DSL scripts in case it has dependencies on other actions
                    self._resolve_dsl_scripts(
                        self.automation_state.automation.actions_dag.get_executable_actions(),
                        True
                    )
                # fetch the dependencies of the automation environment
                fetched_dependencies = await self._fetch_dependencies(maybe_community_repository, to_execute_actions)
                # Align on the previous scheduled time when possible when running priority actions
                # to keep sleep cycles consistency when a priority action is processed.
                default_next_execution_scheduled_to = (
                    self.automation_state.automation.execution.current_execution.scheduled_to
                    if are_priority_actions else 0
                )
                # execute the automation
                executed_actions = await self._execute_automation_actions(
                    maybe_community_repository, fetched_dependencies, to_execute_actions,
                    default_next_execution_scheduled_to
                )
                # don't keep resolved DSL scripts after execution to avoid side effects
                self._clear_resolved_dsl_scripts(executed_actions)
        self._logger.info(f"Automation updated successfully in {round(time.time() - t0, 2)} seconds")
        return executed_actions

    @contextlib.asynccontextmanager
    async def _maybe_authenticator(self) -> typing.AsyncGenerator[typing.Optional[octobot.community.CommunityAuthentication], None]:
        authenticator_factory = octobot_flow.repositories.community.CommunityAuthenticatorFactory(
            self.auth_details
        )
        if authenticator_factory.enable_community_authentication():
            if self.auth_details.has_auth_details():
                async with authenticator_factory.local_authenticator() as authenticator:
                    yield authenticator
            else:
                async with authenticator_factory.local_anon_authenticator() as authenticator:
                    yield authenticator
        else:
            yield None

    async def execute_initialization_run(self) -> list[octobot_flow.entities.AbstractActionDetails]:
        executed_actions = []
        async with self._maybe_authenticator() as maybe_authenticator:
            await self._fetch_actions(maybe_authenticator)
            executed_actions = await self._initialize_exchange_account_details_from_actions()
        if self._requires_initialization_run():
            raise octobot_flow.errors.InitializationRunFailedError(
                "Initialization run is still required after running the initialization run"
            )
        self._logger.info(
            f"Initialization run completed, automation initialized on "
            f"{self.automation_state.exchange_account_details.exchange_details.internal_name}"
        )
        return executed_actions

    async def _initialize_exchange_account_details_from_actions(self) -> list[octobot_flow.entities.AbstractActionDetails]:
        already_applied_config = False
        actions, _ = self._get_actions_to_execute()
        for action in actions:
            if isinstance(action, octobot_flow.entities.ConfiguredActionDetails) and action.action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value:
                if already_applied_config:
                    raise octobot_flow.errors.InitializationRunFailedError(
                        "Only one configuration action is allowed"
                    )
                await self._apply_configuration_from_action(action)
                already_applied_config = True
            else:
                self._logger.info(f"Ignoring non configuration action before initialization: {action}")
        return actions

    async def _apply_configuration_from_action(
        self, action: octobot_flow.entities.ConfiguredActionDetails
    ):
        if self.automation_state.exchange_account_details is None:
            self.automation_state.exchange_account_details = octobot_flow.entities.ExchangeAccountDetails()
        action_configuration_updater = octobot_flow.logic.configuration.AutomationConfigurationUpdater(
            self.automation_state, action
        )
        await action_configuration_updater.update()

    async def _fetch_actions(
        self, maybe_authenticator: typing.Optional[octobot.community.CommunityAuthentication]
    ):
        automation = self.automation_state.automation
        if automation.execution.should_fetch_custom_actions_or_signals():
            user_actions_to_fetch = automation.execution.current_execution.custom_action_ids
            signals_to_fetch = automation.execution.current_execution.signal_ids
            if user_actions_to_fetch or signals_to_fetch:
                authenticator = octobot_flow.repositories.community.ensure_is_authenticated(maybe_authenticator)
                t0 = time.time()
                all_actions: list[octobot_flow.entities.AbstractActionDetails] = []
                repository = octobot_flow.repositories.community.CustomActionsRepository(authenticator)
                if user_actions_to_fetch:
                    all_actions.extend(await repository.fetch_custom_actions(
                        user_actions_to_fetch, select_pending_user_actions_only=True
                    ))
                if signals_to_fetch:
                    all_actions.extend(await repository.fetch_signals(
                        signals_to_fetch, select_pending_signals_only=True
                    ))
                self._logger.info(
                    f"Fetched {len(all_actions)} custom actions/signals for automation "
                    f"{automation.metadata.automation_id} in {round(time.time() - t0, 2)} seconds"
                )
                self.fetched_actions.extend(all_actions)

    def _requires_initialization_run(self) -> bool:
        return (
            self.automation_state.automation.execution.previous_execution.triggered_at == 0
            and (
                not self.automation_state.exchange_account_details
                or not self.automation_state.exchange_account_details.exchange_details.internal_name
            )
        )

    async def _fetch_dependencies(
        self,
        maybe_community_repository: typing.Optional[octobot_flow.repositories.community.CommunityRepository],
        to_execute_actions: list[octobot_flow.entities.AbstractActionDetails]
    ) -> octobot_flow.entities.FetchedDependencies:
        self._logger.info("Fetching automation dependencies.")
        fetched_exchange_data = (
            await self._init_all_required_exchange_data(
                self.automation_state.exchange_account_details, maybe_community_repository, to_execute_actions
            )
            if self.automation_state.has_exchange() else None
        )
        return octobot_flow.entities.FetchedDependencies(
            fetched_exchange_data=fetched_exchange_data
        )

    async def _init_all_required_exchange_data(
        self,
        exchange_account_details: octobot_flow.entities.ExchangeAccountDetails,
        maybe_community_repository: typing.Optional[octobot_flow.repositories.community.CommunityRepository],
        to_execute_actions: list[octobot_flow.entities.AbstractActionDetails]
    ) -> octobot_flow.entities.FetchedExchangeData:
        t0 = time.time()
        exchange_summary = (
            f"[{exchange_account_details.exchange_details.internal_name}]"
            f"account with id: {exchange_account_details.exchange_details.exchange_account_id}"
        )
        self._logger.info(f"Initializing all required data for {exchange_summary}.")
        exchange_account_job = exchange_account_job_import.ExchangeAccountJob(
            self.automation_state, self.fetched_actions
        )
        symbol = set(
            exchange_account_job.get_all_actions_symbols()
            + octobot_flow.logic.dsl.get_actions_symbol_dependencies(to_execute_actions)
        )
        async with exchange_account_job.account_exchange_context(
            octobot_flow.logic.configuration.create_profile_data(
                self.automation_state.exchange_account_details,
                self.automation_state.automation.metadata.automation_id,
                symbol
            )
        ):
            await exchange_account_job.update_public_data()
            self._logger.info(
                f"Public data updated for {exchange_account_details.exchange_details.internal_name} in {round(time.time() - t0, 2)} seconds"
            )
            t1 = time.time()
            await exchange_account_job.update_authenticated_data()
            self._logger.info(
                f"Authenticated data updated for {exchange_account_details.exchange_details.internal_name} in {round(time.time() - t1, 2)} seconds"
            )
        self._logger.info(
            f"Initialized all required data for {exchange_summary} in {round(time.time() - t0, 2)} seconds."
        )
        return exchange_account_job.fetched_dependencies.fetched_exchange_data  # type: ignore

    async def _execute_automation_actions(
        self,
        maybe_community_repository: typing.Optional[octobot_flow.repositories.community.CommunityRepository],
        fetched_dependencies: octobot_flow.entities.FetchedDependencies,
        to_execute_actions: list[octobot_flow.entities.AbstractActionDetails],
        default_next_execution_scheduled_to: float
    ) -> list[octobot_flow.entities.AbstractActionDetails]:
        automation_runner_job = automation_runner_job_import.AutomationRunnerJob(
            self.automation_state, fetched_dependencies, maybe_community_repository,
            default_next_execution_scheduled_to
        )
        automation = self.automation_state.automation
        exchange_account_desc = (
            'simulated exchange account' if self.automation_state.exchange_account_details.is_simulated()
            else 'real exchange account'
        )
        automation_signature = f"{exchange_account_desc} automation {automation.metadata.automation_id}"
        try:
            self._logger.info(f"Updating {automation_signature}")
            automation_runner_job.validate(automation)
            start_time = time.time()
            run_as_reference_account_first = automation.runs_on_reference_exchange_account_first()
            async with automation_runner_job.actions_context(
                to_execute_actions,
                run_as_reference_account_first
            ):
                await automation_runner_job.run()
            if run_as_reference_account_first:
                raise NotImplementedError("TODO: implement copy from reference account to client account")
            self._logger.info(
                f"{automation_signature} successfully updated in {round(time.time() - start_time, 2)} seconds"
            )
        except octobot_flow.errors.AutomationValidationError as err:
            self._logger.exception(
                err, True, f"Skipped {automation_signature} update: automation configuration is invalid: {err}"
            )
        except Exception as err:
            self._logger.exception(
                err,
                True,
                f"Unexpected error when updating {automation_signature}: {err.__class__.__name__}: {err}"
            )
        return to_execute_actions

    def _get_actions_to_execute(self) -> tuple[list[octobot_flow.entities.AbstractActionDetails], bool]:
        if pending_priority_actions := self._get_pending_priority_actions():
            return pending_priority_actions, True
        executable_actions = self.automation_state.automation.actions_dag.get_executable_actions()
        return executable_actions + self.fetched_actions, False

    def _get_pending_priority_actions(self) -> list[octobot_flow.entities.AbstractActionDetails]:
        return [
            action for action in self.automation_state.priority_actions if not action.is_completed()
        ]

    def _resolve_dsl_scripts(
        self, actions: list[octobot_flow.entities.AbstractActionDetails],
        from_actions_dag: bool
    ):
        if from_actions_dag:
            self.automation_state.automation.actions_dag.resolve_dsl_scripts(
                actions
            )
        else:
            local_dag = octobot_flow.entities.ActionsDAG(actions=actions)
            local_dag.resolve_dsl_scripts(actions)

    def _clear_resolved_dsl_scripts(self, actions: list[octobot_flow.entities.AbstractActionDetails]):
        for action in actions:
            if isinstance(action, octobot_flow.entities.DSLScriptActionDetails):
                action.clear_resolved_dsl_script()

    def dump(self) -> dict:
        return octobot_flow.parsers.sanitizer.sanitize(
            self.automation_state.to_dict(include_default_values=False)
        )  # type: ignore

    async def __aenter__(self) -> "AutomationJob":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        # nothing to do for now
        pass

    def _validate_input(self):
        if not self.automation_state.automation.metadata.automation_id:
            raise octobot_flow.errors.NoAutomationError("Automation is required")
