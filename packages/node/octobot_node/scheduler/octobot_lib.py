#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import typing
import dataclasses
import json
import logging

import octobot_commons.list_util as list_util
import octobot_commons.dataclasses

import octobot_tentacles_manager.api

try:
    import mini_octobot
    import mini_octobot.environment
    import mini_octobot.enums
    import mini_octobot.parsers
    # Requires mini_octobot import and importable tentacles folder

    # ensure environment is initialized
    mini_octobot.environment.initialize_environment(True)
    # reload tentacles info to ensure mini-octobot tentacles are loaded
    octobot_tentacles_manager.api.reload_tentacle_info()
    import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators
    import tentacles.Meta.DSL_operators.blockchain_wallet_operators as blockchain_wallet_operators


except ImportError:
    logging.getLogger("octobot_node.scheduler.octobot_lib").warning("OctoBot is not installed, OctoBot actions will not be available")
    # mocks to allow import
    class mini_octobot_mock:
        class AbstractActionDetails:
            def from_dict(self, *args, **kwargs):
                raise NotImplementedError("AbstractActionDetails.from_dict is not implemented")

        class AutomationsState:
            def from_dict(self, *args, **kwargs):
                raise NotImplementedError("AutomationsState.from_dict is not implemented")
            def to_dict(self, *args, **kwargs):
                raise NotImplementedError("AutomationsState.to_dict is not implemented")
            def add_new_automation(self, *args, **kwargs):
                raise NotImplementedError("AutomationsState.add_new_automation is not implemented")
            def upsert_automation_actions(self, *args, **kwargs):
                raise NotImplementedError("AutomationsState.upsert_automation_actions is not implemented")
        class parsers:
            class ActionsDAGParser:
                def __init__(self, *args, **kwargs):
                    raise NotImplementedError("ActionsDAGParser.__init__ is not implemented")
                def parse(self, *args, **kwargs):
                    raise NotImplementedError("ActionsDAGParser.parse is not implemented")

        class AutomationsJob:
            def __init__(self, *args, **kwargs):
                raise NotImplementedError("AutomationsJob.__init__ is not implemented")
            async def __aenter__(self):
                raise NotImplementedError("AutomationsJob.__aenter__ is not implemented")
            async def __aexit__(self, *args, **kwargs):
                raise NotImplementedError("AutomationsJob.__aexit__ is not implemented")
    mini_octobot = mini_octobot_mock()


@dataclasses.dataclass
class OctoBotActionsJobDescription(octobot_commons.dataclasses.MinimizableDataclass):
    state: dict = dataclasses.field(default_factory=dict)
    auth_details: dict = dataclasses.field(default_factory=dict)
    params: dict = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        if self.params:
            self._parse_actions_plan(self.params)

    def _parse_actions_plan(self, params: dict) -> None:
        to_add_actions_dag = mini_octobot.parsers.ActionsDAGParser(params).parse()
        if not to_add_actions_dag:
            raise ValueError("No action found in params")
        automation_id = None
        if isinstance(to_add_actions_dag.actions[0], mini_octobot.entities.ConfiguredActionDetails):
            automation_id = to_add_actions_dag.actions[0].config["automations"][0]["metadata"]["automation_id"]
        if not automation_id:
            raise ValueError("No automation id found in params")
        self._include_actions_in_automations_state(automation_id, to_add_actions_dag)
    
    def _include_actions_in_automations_state(self, automation_id: str, actions: mini_octobot.ActionsDAG):
        automations_state = mini_octobot.AutomationsState.from_dict(self.state)
        if not automations_state.automations:
            automations_state.add_new_automation(
                automation_id, actions,
            )
        else:
            automations_state.upsert_automation_actions(
                automation_id, actions,
            )
        self.state = automations_state.to_dict(include_default_values=False)

    def get_next_execution_time(self) -> float:
        return min(
            automation["execution"]["current_execution"]["scheduled_to"]
            for automation in self.state["automations"]
        )


def required_actions(func):
    def get_required_actions_wrapper(self, *args, **kwargs):
        if self.processed_actions_by_automation_id is None:
            raise ValueError("No bot actions were executed yet")
        return func(self, *args, **kwargs)
    return get_required_actions_wrapper


@dataclasses.dataclass
class OctoBotActionsJobResult:
    processed_actions_by_automation_id: dict[str, list[mini_octobot.AbstractActionDetails]]
    next_actions_description: typing.Optional[OctoBotActionsJobDescription] = None
    actions_dag_by_automation_id: dict[str, mini_octobot.ActionsDAG] = dataclasses.field(default_factory=dict)

    @required_actions
    def get_failed_actions(self) -> list[dict]:
        failed_actions = [
            action.result
            for actions in self.processed_actions_by_automation_id.values()
            for action in actions
            if action.error_status is not mini_octobot.enums.ActionErrorStatus.NO_ERROR.value
        ]
        return failed_actions

    @required_actions
    def get_created_orders(self) -> list[dict]:
        order_lists = [
            action.result.get(exchange_operators.CREATED_ORDERS_KEY, [])
            for actions in self.processed_actions_by_automation_id.values()
            for action in actions
            if action.result
        ]
        return list_util.flatten_list(order_lists) if order_lists else []

    @required_actions
    def get_cancelled_orders(self) -> list[str]:
        cancelled_orders = [
            action.result.get(exchange_operators.CANCELLED_ORDERS_KEY, [])
            for actions in self.processed_actions_by_automation_id.values()
            for action in actions
            if action.result
        ]
        return list_util.flatten_list(cancelled_orders) if cancelled_orders else []
    
    @required_actions
    def get_deposit_and_withdrawal_details(self) -> list[dict]:
        withdrawal_lists = [
            action.result.get(exchange_operators.CREATED_WITHDRAWALS_KEY, []) + action.result.get(blockchain_wallet_operators.CREATED_TRANSACTIONS_KEY, [])
            for actions in self.processed_actions_by_automation_id.values()
            for action in actions
            if action.result and isinstance(action.result, dict) and (
                exchange_operators.CREATED_WITHDRAWALS_KEY in action.result or
                blockchain_wallet_operators.CREATED_TRANSACTIONS_KEY in action.result
            )
        ]
        return list_util.flatten_list(withdrawal_lists) if withdrawal_lists else []


class OctoBotActionsJob:
    def __init__(self, description: typing.Union[str, dict]):
        parsed_description = self._parse_description(description)
        self.description: OctoBotActionsJobDescription = OctoBotActionsJobDescription.from_dict(
            parsed_description
        )
        self.after_execution_state = None

    def _parse_description(self, description: typing.Union[str, dict]) -> dict:
        if isinstance(description, dict):
            # normal Non-init case
            parsed_description = description
        else:
            dict_description = json.loads(description)
            if "state" in dict_description:
                # there is a state, so it's a non init case
                parsed_description = dict_description
            else:
                # normal init case: description is a JSON string: store it in params
                parsed_description = {
                    "params": dict_description
                }
                # TMP: add a simulated portfolio to the params
                parsed_description["params"]["SIMULATED_PORTFOLIO"] = {
                    "ETH": 1,
                }
        return parsed_description

    async def run(self) -> OctoBotActionsJobResult:
        async with mini_octobot.AutomationsJob(
            self.description.state, self.description.auth_details
        ) as automations_job:
            selected_actions_by_automation = {
                automation.metadata.automation_id: automation.actions_dag.get_executable_actions()
                for automation in automations_job.automations_state.automations
            }
            logging.getLogger(self.__class__.__name__).info(f"Running automations actions: {selected_actions_by_automation}")
            await automations_job.run()
            for automation_id, selected_actions in selected_actions_by_automation.items():
                automations_job.automations_state.get_automation_details(automation_id).actions_dag.update_actions_results(selected_actions)
            self.after_execution_state = automations_job.automations_state
            post_execution_state_dump = automations_job.dump()
            return OctoBotActionsJobResult(
                processed_actions_by_automation_id=selected_actions_by_automation,
                next_actions_description=self.get_next_actions_description(post_execution_state_dump),
                actions_dag_by_automation_id={
                    automation.metadata.automation_id: automation.actions_dag
                    for automation in automations_job.automations_state.automations
                },
            )

    def get_next_actions_description(
        self, post_execution_state: dict
    ) -> typing.Optional[OctoBotActionsJobDescription]:
        has_at_least_one_action_to_execute = False
        for automation in self.after_execution_state.automations:
            if automation.actions_dag.get_executable_actions():
                has_at_least_one_action_to_execute = True
            else:
                if pending_actions := automation.actions_dag.get_pending_actions():
                    raise ValueError(
                        f"Automation {automation.metadata.automation_id}: actions DAG dependencies issue: "
                        f"no executable actions while there are still "
                        f"{len(pending_actions)} pending actions: {pending_actions}"
                    )
        if has_at_least_one_action_to_execute:
            return OctoBotActionsJobDescription(
                state=post_execution_state,
                auth_details=self.description.auth_details,
            )
        return None

    def __repr__(self) -> str:
        parsed_state = mini_octobot.AutomationsState.from_dict(self.description.state)
        automations_repr = (
            '\n- '.join([str(automation) for automation in parsed_state.automations])
            if parsed_state.automations
            else "No automations"
        )
        return (
            f"OctoBotActionsJob with {len(parsed_state.automations)} "
            f"automation{'s' if len(parsed_state.automations) > 1 else ''}:\n- {automations_repr})"
        )