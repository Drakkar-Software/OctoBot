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
import uuid

import octobot_flow.entities as flow_entities
import octobot_protocol.models as protocol_models

import octobot_node.constants as constants
import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.automation.automation_user_action_executor as automation_user_action_executor
import octobot_node.scheduler.user_actions.user_actions_executor.util.action_details_factory as action_details_factory

import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers

import octobot_node.models as models
import octobot_node.scheduler.tasks


def _validate_automation_configuration_id(automation_id: str) -> None:
    try:
        parsed_uuid = uuid.UUID(automation_id)
    except ValueError as err:
        raise node_errors.InvalidAutomationIdError(
            f"AutomationConfiguration.id must be a valid UUID, got {automation_id!r}"
        ) from err
    canonical_id = str(parsed_uuid)
    if canonical_id != automation_id:
        raise node_errors.InvalidAutomationIdError(
            f"AutomationConfiguration.id must be canonical lowercase UUID form, got {automation_id!r}"
        )
    if len(automation_id) != constants.PARENT_WORKFLOW_ID_LENGTH:
        raise node_errors.InvalidAutomationIdError(
            f"AutomationConfiguration.id must be {constants.PARENT_WORKFLOW_ID_LENGTH} characters, "
            f"got {len(automation_id)} for {automation_id!r}"
        )


def _resolve_create_automation_id(
    user_action: protocol_models.UserAction,
    automation_configuration: protocol_models.AutomationConfiguration,
) -> str:
    if automation_configuration.id:
        return automation_configuration.id
    return user_action.id


def _execute_actions_task_content_json(
    *,
    automation_id: str,
    actions: list[flow_entities.AbstractActionDetails],
) -> str:
    """
    Build Task.content for EXECUTE_ACTIONS: JSON envelope with automation state and actions DAG,
    matching octobot_node.scheduler.workflows_util.get_automation_dict / functional workflow tests.
    """
    automation_state = flow_entities.AutomationState(
        automation=flow_entities.AutomationDetails(
            metadata=flow_entities.AutomationMetadata(automation_id=automation_id),
            actions_dag=flow_entities.ActionsDAG(actions=actions),
        ),
    )
    return json.dumps({"state": automation_state.to_dict(include_default_values=False)})


def _load_strategy_for_automation(
    user_id: str,
    strategy_reference: protocol_models.StrategyReference,
) -> protocol_models.Strategy:
    try:
        stored_strategy = collection_providers.StrategyProvider.instance().get_item(
            user_id,
            strategy_reference.id,
        )
    except collection_errors.ItemNotFoundError as err:
        raise node_errors.AutomationStrategyNotFoundError(
            f"Strategy {strategy_reference.id!r} not found for address {user_id!r}"
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
        if automation_configuration.id:
            _validate_automation_configuration_id(automation_configuration.id)
        automation_id = _resolve_create_automation_id(user_action, automation_configuration)
        task_fields = {
            "name": automation_configuration.name,
            "content": _execute_actions_task_content_json(automation_id=automation_id, actions=actions),
            "type": models.TaskType.EXECUTE_ACTIONS.value,
            "user_id": self._user_id,
        }
        if automation_configuration.id:
            task_fields["id"] = automation_configuration.id
        return models.Task(**task_fields)

    def _get_automation_configuration(self, user_action: protocol_models.UserAction) -> protocol_models.AutomationConfiguration:
        create_payload = _get_create_automation_payload(user_action)
        return create_payload.configuration

    def _create_automation_actions(self, user_action: protocol_models.UserAction) -> list[flow_entities.AbstractActionDetails]:
        automation_configuration = self._get_automation_configuration(user_action)
        if automation_configuration.id:
            _validate_automation_configuration_id(automation_configuration.id)
        automation_id = _resolve_create_automation_id(user_action, automation_configuration)

        stored_strategy = _load_strategy_for_automation(
            self._user_id,
            automation_configuration.strategy,
        )
        inner_configuration = _get_strategy_configuration_instance(stored_strategy)

        account_id = _get_single_account_id(automation_configuration)

        try:
            protocol_account = collection_providers.AccountProvider.instance().get_item(
                self._user_id,
                account_id,
            )
        except collection_errors.ItemNotFoundError as err:
            raise node_errors.AccountNotFoundError(
                f"Failed to load account {account_id!r} for address {self._user_id!r}: {err}"
            ) from err

        init_action = action_details_factory.init_action_factory(
            automation_id=automation_id,
            protocol_account=protocol_account,
            strategy_reference=automation_configuration.strategy,
            stored_strategy=stored_strategy,
            user_id=self._user_id,
            reference_market=stored_strategy.reference_market,
        )

        match inner_configuration:
            case protocol_models.TradingTentaclesConfiguration() as trading_configuration:
                action_details_factory.validate_tentacles_config(
                    trading_configuration
                )
                if trading_configuration.evaluators:
                    return action_details_factory.trading_tentacles_with_evaluators_actions_factory(
                        init_action,
                        trading_configuration,
                    )
                return [
                    init_action,
                    action_details_factory.trading_tentacles_action_factory(
                        init_action,
                        trading_configuration,
                    ),
                ]
            case protocol_models.GenericProcessConfiguration() as generic_process_configuration:
                return [
                    init_action,
                    action_details_factory.generic_process_action_factory(
                        init_action,
                        generic_process_configuration,
                        protocol_account,
                        self._user_id,
                        automation_id=automation_id,
                    ),
                ]
            case protocol_models.CopyConfiguration() as copy_configuration:
                return [
                    init_action,
                    action_details_factory.copy_action_factory(
                        init_action,
                        copy_configuration,
                        reference_market=stored_strategy.reference_market,
                    ),
                ]
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
                        self._user_id,
                        stored_strategy.reference_market,
                        stored_strategy,
                        automation_id=automation_id,
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
