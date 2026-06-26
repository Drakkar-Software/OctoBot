import contextlib
import time
import typing

import octobot_commons.json_util as json_util
import octobot_commons.logging as common_logging
import octobot.community
import octobot.community.wallet_backend.errors as wallet_backend_errors
import octobot_commons.profiles.profile_data as profile_data_import

import octobot_copy.constants as copy_constants

import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.errors
import octobot_flow.logic.actions
import octobot_flow.logic.configuration
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
        updated_trading_signals: list[octobot_flow.entities.TradingSignal],
        auth_details: typing.Union[octobot_flow.entities.UserAuthentication, dict],
    ):
        self.automation_state: octobot_flow.entities.AutomationState = (
            octobot_flow.entities.AutomationState.from_dict(automation_state)
        )
        if added_priority_actions:
            # Include added priority actions in the automation state. 
            # All pending priority actions will be executed before any other actions.
            self.automation_state.update_priority_actions(added_priority_actions)
        if updated_trading_signals:
            default_reference_market = octobot_flow.logic.configuration.infer_reference_market(
                self.automation_state.exchange_account_details, [],
            )
            octobot_flow.logic.actions.update_trading_signals(
                self.automation_state.automation.actions_dag.actions,
                updated_trading_signals,
                default_reference_market,
            )
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
                octobot_flow.repositories.community.CommunityRepository(
                    maybe_authenticator,
                    wallet_address=self.auth_details.wallet_address,
                )
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
                    self._resolve_dsl_scripts(to_execute_actions, True)
                # fetch the dependencies of the automation environment
                fetched_dependencies = await self._fetch_dependencies(
                    maybe_community_repository, to_execute_actions, 
                )
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

    def update_actions_from_copy_trading_data(
        self,
        actions: list[octobot_flow.entities.AbstractActionDetails],
        copy_trading_data: octobot_flow.entities.FetchedCopyTradingData,
        default_reference_market: str,
    ):
        # adapt actions to reflect the new trading signals
        for trading_signal in copy_trading_data.trading_signals:
            for action in actions:
                try:
                    octobot_flow.logic.actions.update_action_trading_signal_if_relevant(
                        action, trading_signal, default_reference_market
                    )
                except octobot_flow.errors.CommunityTradingSignalError:
                    # Signal applies to a different strategy than this copy_exchange_account action.
                    continue

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
        to_execute_actions: list[octobot_flow.entities.AbstractActionDetails],
    ) -> octobot_flow.entities.FetchedDependencies:
        self._logger.info("Fetching automation dependencies.")
        minimal_profile_data = octobot_flow.logic.configuration.create_profile_data(
            self.automation_state.exchange_account_details,
            self.automation_state.automation.metadata.automation_id,
            set()
        )
        dag_actions = self.automation_state.automation.actions_dag.get_executable_actions()
        # check are_all_actions_process_bound_only from dag actions only
        if octobot_flow.logic.dsl.are_all_actions_process_bound_only(
            minimal_profile_data, dag_actions
        ):
            self._logger.info(
                "Skipping copy-trading and exchange dependency initialization (process-bound DSL actions only)."
            )
            return octobot_flow.entities.FetchedDependencies(
                fetched_exchange_data=None,
                fetched_copy_trading_data=None,
            )
        if fetched_copy_trading_data := await self._init_all_required_copy_trading_data(
            maybe_community_repository, to_execute_actions, minimal_profile_data,
        ):
            default_reference_market = octobot_flow.logic.configuration.infer_reference_market(
                self.automation_state.exchange_account_details, [],
            )
            self.update_actions_from_copy_trading_data(
                to_execute_actions, fetched_copy_trading_data, default_reference_market
            )
        fetched_exchange_data = (
            await self._init_all_required_exchange_data(
                self.automation_state.exchange_account_details,
                maybe_community_repository, to_execute_actions,
                minimal_profile_data,
            )
            if self.automation_state.has_exchange() else None
        )
        return octobot_flow.entities.FetchedDependencies(
            fetched_exchange_data=fetched_exchange_data,
            fetched_copy_trading_data=fetched_copy_trading_data,
        )

    async def _init_all_required_exchange_data(
        self,
        exchange_account_details: octobot_flow.entities.ExchangeAccountDetails,
        maybe_community_repository: typing.Optional[octobot_flow.repositories.community.CommunityRepository],
        to_execute_actions: list[octobot_flow.entities.AbstractActionDetails],
        minimal_profile_data: profile_data_import.ProfileData,
    ) -> octobot_flow.entities.FetchedExchangeData:
        t0 = time.time()
        exchange_summary = (
            f"[{exchange_account_details.exchange_details.internal_name}] "
            f"account with id: {exchange_account_details.exchange_details.exchange_account_id}"
        )
        self._logger.info(f"Initializing all required data for {exchange_summary}.")
        to_execute_actions_ids = {
            executable_action.id for executable_action in to_execute_actions
        }
        actions_for_exchange_data_fetch = to_execute_actions + [
            action for action in self.fetched_actions
            if action.id not in to_execute_actions_ids
        ]
        exchange_account_job = exchange_account_job_import.ExchangeAccountJob(
            self.automation_state, actions_for_exchange_data_fetch
        )
        symbols = set(
            exchange_account_job.get_all_actions_symbols(minimal_profile_data)
            + octobot_flow.logic.dsl.get_actions_symbol_dependencies(
                to_execute_actions, minimal_profile_data
            )
        )
        account_elements = self.automation_state.automation.exchange_account_elements
        if account_elements is not None:
            symbols.update(account_elements.get_open_orders_symbols())
        async with exchange_account_job.account_exchange_context(
            octobot_flow.logic.configuration.create_profile_data(
                self.automation_state.exchange_account_details,
                self.automation_state.automation.metadata.automation_id,
                symbols,
                as_simulator=None,
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

    async def _init_all_required_copy_trading_data(
        self,
        maybe_community_repository: typing.Optional[octobot_flow.repositories.community.CommunityRepository],
        to_execute_actions: list[octobot_flow.entities.AbstractActionDetails],
        minimal_profile_data: profile_data_import.ProfileData,
    ) -> typing.Optional[octobot_flow.entities.FetchedCopyTradingData]:
        copy_trading_data = None
        if to_fetch_signals := [
            copy_trading_dependency.strategy_id
            for copy_trading_dependency in octobot_flow.logic.dsl.get_copy_trading_dependencies(
                to_execute_actions, minimal_profile_data
            )
            if copy_trading_dependency.refresh_required
        ]:
            if maybe_community_repository is None:
                raise octobot_flow.errors.CommunityTradingSignalError(
                    "Community authentication is required to fetch copy trading signals"
                )
            trading_signals_repository = octobot_flow.repositories.community.TradingSignalsRepository.from_community_repository(maybe_community_repository)
            self._logger.info(f"Fetching copy trading signals for {to_fetch_signals} strategies")
            trading_signals = await trading_signals_repository.fetch_trading_signals(
                to_fetch_signals,
                copy_constants.DEFAULT_MISSED_SIGNALS_GRACE_ABORT_THRESHOLD,
            )
            self._logger.info(f"Fetched {len(trading_signals)} copy trading signals")
            fetched_strategy_ids = {trading_signal.strategy_id for trading_signal in trading_signals}
            missing_strategy_ids = set(to_fetch_signals) - fetched_strategy_ids
            if missing_strategy_ids:
                missing_strategy_ids_list = ", ".join(sorted(missing_strategy_ids))
                raise octobot_flow.errors.CommunityTradingSignalError(
                    f"No trading signal available for strategy {missing_strategy_ids_list}. "
                    "The leader automation must complete at least one iteration with "
                    "`emit_signals` enabled before copy can run."
                )
            copy_trading_data = octobot_flow.entities.FetchedCopyTradingData(
                trading_signals=trading_signals
            )
        return copy_trading_data

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
            async with automation_runner_job.actions_context(
                to_execute_actions,
                update_execution_details=True,
            ):
                await automation_runner_job.run()
            self._logger.info(
                f"{automation_signature} successfully updated in {round(time.time() - start_time, 2)} seconds"
            )
            if automation.metadata.emit_signals:
                await self._emit_trading_signals(
                    maybe_community_repository, automation, fetched_dependencies
                )
        except octobot_flow.errors.AutomationValidationError as err:
            self._logger.error(
                f"{automation_signature} automation configuration is invalid: {err}"
            )
            raise
        except Exception as err:
            self._logger.error(
                f"Unexpected error when updating {automation_signature}: {err.__class__.__name__}: {err}"
            )
            raise
        return to_execute_actions

    async def _emit_trading_signals(
        self,
        maybe_community_repository: typing.Optional[octobot_flow.repositories.community.CommunityRepository],
        automation: octobot_flow.entities.AutomationDetails,
        fetched_dependencies: octobot_flow.entities.FetchedDependencies,
    ):
        if not maybe_community_repository:
            raise octobot_flow.errors.CommunityTradingSignalError(
                "Community authentication is required to emit trading signals"
            )
        reference_market = octobot_flow.logic.configuration.infer_reference_market(
            self.automation_state.exchange_account_details, [],
        )
        account = octobot_flow.logic.actions.reference_exchange_elements_to_account(
            automation.exchange_account_elements,
            fetched_dependencies.fetched_exchange_data,
            reference_market
        )
        trading_signals_repository = octobot_flow.repositories.community.TradingSignalsRepository.from_community_repository(
            maybe_community_repository
        )
        try:
            await trading_signals_repository.insert_trading_signal(
                octobot_flow.entities.TradingSignal(
                    strategy_id=automation.metadata.strategy_id, account=account
                )
            )
        except wallet_backend_errors.WalletNotFoundError as err:
            self._logger.error(
                f"Skipping trading signal emission: {err}"
            )
            
    def _get_actions_to_execute(self) -> tuple[list[octobot_flow.entities.AbstractActionDetails], bool]:
        if pending_priority_actions := self._get_pending_priority_actions():
            return pending_priority_actions, True
        executable_actions = self.automation_state.automation.actions_dag.get_executable_actions()
        return executable_actions + self.fetched_actions, False

    def _get_pending_priority_actions(self) -> list[octobot_flow.entities.AbstractActionDetails]:
        return self.automation_state.get_pending_priority_actions()

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
        return json_util.sanitize(
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
