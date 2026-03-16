import contextlib
import typing

import octobot_commons.profiles as commons_profiles
import octobot_commons.context_util as context_util
import octobot_trading.util.test_tools.exchange_data as exchange_data_import

import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.errors
import octobot_flow.logic.configuration
import octobot_flow.logic.dsl
import octobot_flow.repositories.exchange
import octobot_flow.repositories.community
import octobot_flow.logic.actions


class AutomationRunnerJob(octobot_flow.repositories.exchange.ExchangeContextMixin):
    """
    Runs the automation from the configured environment.
    Sequentially executes the automation pre-actions, actions and post-actions.
    Finally, completes the current execution and register the next execution scheduled time.
    """
    WILL_EXECUTE_STRATEGY: bool = True

    def __init__(
        self,
        automation_state: octobot_flow.entities.AutomationState,
        fetched_dependencies: octobot_flow.entities.FetchedDependencies,
        maybe_community_repository: typing.Optional[octobot_flow.repositories.community.CommunityRepository],
        default_next_execution_scheduled_to: float,
    ):
        super().__init__(automation_state, fetched_dependencies)

        self._maybe_community_repository: typing.Optional[
            octobot_flow.repositories.community.CommunityRepository
        ] = maybe_community_repository
        self._as_reference_account: bool = False
        self._to_execute_actions: list[octobot_flow.entities.AbstractActionDetails] = None # type: ignore
        self._default_next_execution_scheduled_to: float = default_next_execution_scheduled_to

    def validate(self, automation: octobot_flow.entities.AutomationDetails):
        if not automation.metadata.automation_id:
            raise octobot_flow.errors.AutomationValidationError(
                f"automation_id is required. Found: {automation.metadata.automation_id}"
            )

    async def run(self):
        self.automation_state.automation.execution.start_execution()
        # 1. for each automation, process additional actions if necessary (ex: portfolio optimization)
        if self.automation_state.automation.execution.current_execution.additional_actions.has_trading_actions():
            await self._process_additional_actions()
        # 2. process on filled and cancelled orders actions if necessary
        await self._process_on_filled_and_cancelled_orders_actions()
        # 3. update strategy if necessary
        changed_elements, next_execution_scheduled_to = await self._execute_actions()
        if octobot_flow.enums.ChangedElements.ORDERS in changed_elements:
            # 4. process on filled and cancelled orders actions again if necessary
            await self._process_on_filled_and_cancelled_orders_actions()
        # 5. execute post actions if necessary
        if self.automation_state.automation.post_actions.has_automation_actions():
            await self._execute_post_actions()
        # 6. register execution completion
        self.automation_state.automation.execution.complete_execution(next_execution_scheduled_to)

    async def _execute_actions(self) -> tuple[list[octobot_flow.enums.ChangedElements], float]:
        actions_executor = octobot_flow.logic.actions.ActionsExecutor(
            self._maybe_community_repository, self._exchange_manager, 
            self.automation_state.automation, self._to_execute_actions,
            self._as_reference_account
        )
        await actions_executor.execute()
        return actions_executor.changed_elements, (
            # use self._default_next_execution_scheduled_to if set when no next_execution_scheduled_to
            # is configured
            actions_executor.next_execution_scheduled_to or self._default_next_execution_scheduled_to
        )

    async def _process_on_filled_and_cancelled_orders_actions(self):
        # update chained orders, groups and other mechanics if necessary
        if not self.automation_state.has_exchange():
            return
        exchange_account_elements = self.automation_state.automation.get_exchange_account_elements(self._as_reference_account)
        if exchange_account_elements.has_pending_chained_orders():
            await self._update_chained_orders()
        if exchange_account_elements.has_pending_groups():
            await self._update_groups()

    async def _update_chained_orders(self):
        raise NotImplementedError("_update_chained_orders not implemented")

    async def _update_groups(self):
        raise NotImplementedError("_update_groups not implemented")
            
    async def _process_additional_actions(self):
        raise NotImplementedError("_process_additional_actions not implemented")

    async def _stop_automation(self):
        # TODO when supporting sub portfolios: unregister automation sub portfolio 
        pass

    async def _execute_post_actions(self):
        if self.automation_state.automation.post_actions.stop_automation:
            await self._stop_automation()

    def init_strategy_exchange_data(self, exchange_data: exchange_data_import.ExchangeData):
        exchange_account_elements = self.automation_state.automation.get_exchange_account_elements(self._as_reference_account)
        exchange_data.markets = self.fetched_dependencies.fetched_exchange_data.public_data.markets
        exchange_data.portfolio_details.content = exchange_account_elements.portfolio.content
        exchange_data.orders_details.open_orders = exchange_account_elements.orders.open_orders

    def _get_profile_data(self) -> commons_profiles.ProfileData:
        return octobot_flow.logic.configuration.create_profile_data(
            self.automation_state.exchange_account_details,
            self.automation_state.automation.metadata.automation_id,
            set(octobot_flow.logic.dsl.get_actions_symbol_dependencies(
                self._to_execute_actions
            ))
        )

    @contextlib.asynccontextmanager
    async def actions_context(
        self,
        actions: list[octobot_flow.entities.AbstractActionDetails],
        as_reference_account: bool
    ):
        try:
            self._as_reference_account = as_reference_account
            self._to_execute_actions = actions
            with (
                self._maybe_community_repository.automation_context(
                    self.automation_state.automation
                ) if self._maybe_community_repository else context_util.EmptyContextManager(),
                self.profile_data_provider.profile_data_context(self._get_profile_data())
            ):
                if not self.profile_data_provider.get_profile_data().profile_details.bot_id:
                    raise octobot_flow.errors.AutomationValidationError(
                        f"A bot_id is required to run a bot. Found: {self.profile_data_provider.get_profile_data().profile_details.bot_id}"
                    )
                async with self.exchange_manager_context(as_reference_account=self._as_reference_account):
                    yield self
        finally:
            self._to_execute_actions = None # type: ignore
