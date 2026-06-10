#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import json
import typing

import octobot_flow.entities as flow_entities
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.automation.automation_user_action_executor as automation_user_action_executor
import octobot_node.scheduler.user_actions.user_actions_executor.util.action_details_factory as action_details_factory

import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers

import octobot_node.models as models
import octobot_node.scheduler.tasks


def _execute_actions_task_content_json(
    *,
    user_action: protocol_models.UserAction,
    actions: list[flow_entities.AbstractActionDetails],
) -> str:
    """
    Build Task.content for EXECUTE_ACTIONS: JSON envelope with automation state and actions DAG,
    matching octobot_node.scheduler.workflows_util.get_automation_dict / functional workflow tests.
    """
    automation_state = flow_entities.AutomationState(
        automation=flow_entities.AutomationDetails(
            metadata=flow_entities.AutomationMetadata(automation_id=user_action.id),
            actions_dag=flow_entities.ActionsDAG(actions=actions),
        ),
    )
    return json.dumps({"state": automation_state.to_dict(include_default_values=False)})


def _load_strategy_for_automation(
    wallet_address: str,
    strategy_reference: protocol_models.StrategyReference,
) -> protocol_models.Strategy:
    try:
        stored_strategy = collection_providers.StrategyProvider.instance().get_item(
            wallet_address,
            strategy_reference.id,
        )
    except collection_errors.ItemNotFoundError as err:
        raise node_errors.AutomationStrategyNotFoundError(
            f"Strategy {strategy_reference.id!r} not found for address {wallet_address!r}"
        ) from err
    if stored_strategy.version != strategy_reference.version:
        raise node_errors.AutomationStrategyVersionMismatchError(
            f"Strategy {strategy_reference.id!r} version mismatch: automation references "
            f"{strategy_reference.version!r}, stored strategy has {stored_strategy.version!r}"
        )
    return stored_strategy


def _get_strategy_configuration_instance(
    stored_strategy: protocol_models.Strategy,
) -> typing.Any:
    wrapper = stored_strategy.configuration
    if wrapper is None or wrapper.actual_instance is None:
        raise node_errors.InvalidAutomationConfigurationError(
            "Create automation requires Strategy.configuration.actual_instance to be set."
        )
    return wrapper.actual_instance


class CreateAutomationActionExecutor(automation_user_action_executor.AutomationUserActionExecutor):
    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        actions = self._create_automation_actions(user_action)
        task = await self._create_automation_task(user_action, actions)
        self.post_actions.to_create_automation_task = task
        self._mark_user_action_completed(
            user_action,
            created_automation_id=task.id
        )

    async def _create_automation_task(self, user_action, actions: list[flow_entities.AbstractActionDetails]) -> models.Task:
        automation_configuration = self._get_automation_configuration(user_action)
        return models.Task(
            name=automation_configuration.name,
            content=_execute_actions_task_content_json(user_action=user_action, actions=actions),
            type=models.TaskType.EXECUTE_ACTIONS.value,
            wallet_address=self._wallet_address,
        )

    def _get_automation_configuration(self, user_action: protocol_models.UserAction) -> protocol_models.AutomationConfiguration:
        create_payload = _get_create_automation_payload(user_action)
        return create_payload.configuration

    def _create_automation_actions(self, user_action: protocol_models.UserAction) -> list[flow_entities.AbstractActionDetails]:
        automation_configuration = self._get_automation_configuration(user_action)

        stored_strategy = _load_strategy_for_automation(
            self._wallet_address,
            automation_configuration.strategy,
        )
        inner_configuration = _get_strategy_configuration_instance(stored_strategy)

        account_id = _get_single_account_id(automation_configuration)

        try:
            protocol_account = collection_providers.AccountProvider.instance().get_item(
                self._wallet_address,
                account_id,
            )
        except collection_errors.ItemNotFoundError as err:
            raise node_errors.AccountNotFoundError(
                f"Failed to load account {account_id!r} for address {self._wallet_address!r}: {err}"
            ) from err

        init_action = action_details_factory.init_action_factory(
            automation_id=user_action.id,
            protocol_account=protocol_account,
            strategy_reference=automation_configuration.strategy,
            stored_strategy=stored_strategy,
            wallet_address=self._wallet_address,
            reference_market=stored_strategy.reference_market,
        )

        match inner_configuration:
            case protocol_models.DCAConfiguration() as dca_configuration:
                if dca_configuration.evaluators:
                    if not action_details_factory.is_maximum_evaluators_dca_with_evaluators(
                        dca_configuration
                    ):
                        raise node_errors.InvalidAutomationConfigurationError(
                            "DCA configuration with evaluators requires trigger_mode "
                            "'Maximum evaluators signals based' and exactly one strategy evaluator."
                        )
                    return action_details_factory.maximum_evaluators_dca_automation_actions_factory(
                        init_action,
                        dca_configuration,
                    )
                return [init_action, action_details_factory.dca_action_factory(init_action, dca_configuration)]
            case protocol_models.GenericProcessConfiguration():
                raise node_errors.UnsupportedAutomationConfigurationTypeError(
                    f"Unsupported automation configuration type: {protocol_models.ActionConfigurationType.GENERIC_PROCESS.value!r}"
                )
            case protocol_models.IndexConfiguration() as index_configuration:
                return [init_action, action_details_factory.index_action_factory(init_action, index_configuration)]
            case protocol_models.GridConfiguration() as grid_configuration:
                return [init_action, action_details_factory.grid_action_factory(init_action, grid_configuration)]
            case protocol_models.CopyConfiguration() as copy_configuration:
                return [init_action, action_details_factory.copy_action_factory(init_action, copy_configuration)]
            case protocol_models.GenericWorkflowConfiguration() as generic_workflow_configuration:
                workflow_actions = action_details_factory.generic_workflow_actions_factory(
                    init_action,
                    generic_workflow_configuration,
                )
                return [init_action, *workflow_actions]
            case protocol_models.MarketMakingConfiguration() as market_making_configuration:
                return [
                    init_action,
                    action_details_factory.market_making_action_factory(
                        init_action,
                        market_making_configuration,
                        protocol_account,
                        self._wallet_address,
                        stored_strategy.reference_market,
                        stored_strategy,
                    ),
                ]
            case _:
                raise node_errors.UnsupportedAutomationConfigurationTypeError(
                    f"Unknown automation configuration instance type: {type(inner_configuration).__name__}"
                )


def _get_create_automation_payload(
    user_action: protocol_models.UserAction,
) -> protocol_models.CreateAutomationConfiguration:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "UserAction.configuration must wrap a concrete create-automation configuration."
        )
    payload = wrapper.actual_instance
    if not isinstance(payload, protocol_models.CreateAutomationConfiguration):
        raise node_errors.InvalidUserActionPayloadError(
            f"CreateAutomationActionExecutor expected CreateAutomationConfiguration, got {type(payload).__name__}"
        )
    return payload


def _get_single_account_id(automation_configuration: protocol_models.AutomationConfiguration) -> str:
    accounts_list = list(automation_configuration.accounts or [])
    if not accounts_list:
        raise node_errors.InvalidAutomationConfigurationError(
            "Create automation requires AutomationConfiguration.accounts to contain exactly one account reference."
        )
    if len(accounts_list) != 1:
        raise node_errors.InvalidAutomationConfigurationError(
            f"Create automation currently supports exactly one account reference, got {len(accounts_list)}"
        )
    return accounts_list[0].id
