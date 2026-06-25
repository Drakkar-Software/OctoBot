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

import octobot_commons.dataclasses
import octobot_commons.logging

import octobot_node.constants
import octobot_node.errors as errors
import octobot_node.scheduler.workflows_util as workflows_util

try:
    import octobot_flow.environment
    import octobot_flow.parsers
    import octobot_flow.entities
    import octobot_flow.jobs
    import octobot_flow.errors
    # Requires octobot_flow import and importable tentacles folder

    # ensure environment is initialized
    octobot_flow.environment.initialize_environment(True)
    octobot_flow.environment.register_executor_id(
        octobot_node.constants.SCHEDULER_EXECUTOR_ID
    )

except ImportError:
    pass # OctoBot Flow is not available


@dataclasses.dataclass
class OctoBotActionsJobDescription(octobot_commons.dataclasses.MinimizableDataclass):
    state: dict = dataclasses.field(default_factory=dict)
    auth_details: dict = dataclasses.field(default_factory=dict)
    params: dict = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        if self.params:
            self._parse_actions_plan(self.params)

    @staticmethod
    def parse_task_description(description: typing.Union[str, dict]) -> dict:
        try:
            parsed_description = workflows_util.get_automation_dict(description)
        except ValueError:
            if isinstance(description, dict):
                parsed_description = description
            else:
                # description is a JSON string with key/value parameters: store it in params
                dict_description = json.loads(description)
                parsed_description = {
                    "params": dict_description
                }
        return parsed_description


    def _parse_actions_plan(self, params: dict) -> None:
        to_add_actions_dag = octobot_flow.parsers.ActionsDAGParser(params).parse()
        if not to_add_actions_dag:
            raise ValueError("No action found in params")
        automation_id = None
        if not automation_id and isinstance(to_add_actions_dag.actions[0], octobot_flow.entities.ConfiguredActionDetails) and to_add_actions_dag.actions[0].config:
            config = to_add_actions_dag.actions[0].config
            if "automation" in config:
                automation_id = config["automation"]["metadata"]["automation_id"]
        if not automation_id:
            raise ValueError("No automation id found in params")
        self._include_actions_in_automation_state(automation_id, to_add_actions_dag)

    def _include_actions_in_automation_state(self, automation_id: str, actions: "octobot_flow.entities.ActionsDAG"):
        automation_state = octobot_flow.entities.AutomationState.from_dict(self.state)
        if not automation_state.automation.metadata.automation_id:
            automation_state.automation = octobot_flow.entities.AutomationDetails(
                metadata=octobot_flow.entities.AutomationMetadata(
                    automation_id=automation_id,
                ),
                actions_dag=actions,
            )
        else:
            automation_state.upsert_automation_actions(actions.actions)
        self.state = automation_state.to_dict(include_default_values=False)

    def get_next_execution_time(self) -> float:
        return self.state["automation"]["execution"]["current_execution"]["scheduled_to"]


@dataclasses.dataclass
class OctoBotActionsJobResult:
    processed_actions: list["octobot_flow.entities.AbstractActionDetails"] = dataclasses.field(default_factory=list)
    next_actions_description: typing.Optional[OctoBotActionsJobDescription] = None
    maybe_encrypted_next_actions_description: typing.Optional[str] = None
    next_actions_description_encryption_metadata: typing.Optional[str] = None
    has_next_actions: bool = False
    actions_dag: typing.Optional["octobot_flow.entities.ActionsDAG"] = None
    should_stop: bool = False


class OctoBotActionsJob:
    def __init__(
        self,
        description: typing.Union[str, dict],
        user_actions: list[dict],
        updated_trading_signals: list[dict],
        result: OctoBotActionsJobResult,
        wallet_address: typing.Optional[str] = None,
    ):
        try:
            parsed_description = OctoBotActionsJobDescription.parse_task_description(description)
            self.description: OctoBotActionsJobDescription = OctoBotActionsJobDescription.from_dict(
                parsed_description
            )
        except octobot_flow.errors.ActionDependencyError as err:
            raise errors.WorkflowDAGDependenciesError(err) from err
        if wallet_address is not None:
            # auth_details["wallet_address"] carries the EVM address used by automation
            # jobs to build the community sync client (CommunityRepository). It must be
            # the EVM address, not the Starfish user_id.
            self.description.auth_details["wallet_address"] = wallet_address
        self.priority_user_actions: list[octobot_flow.entities.AbstractActionDetails] = [
            octobot_flow.entities.parse_action_details(
                user_action
            ) for user_action in user_actions
        ]
        self.updated_trading_signals: list[octobot_flow.entities.TradingSignal] = [
            octobot_flow.entities.TradingSignal.from_dict(trading_signal_dict)
            for trading_signal_dict in updated_trading_signals
        ]
        self.after_execution_state = None
        self.result: OctoBotActionsJobResult = result

    async def run(self) -> None:
        async with octobot_flow.jobs.AutomationJob(
            self.description.state,
            self.priority_user_actions,
            self.updated_trading_signals,
            self.description.auth_details,
        ) as automation_job:
            selected_actions = (
                self.priority_user_actions
                or automation_job.automation_state.automation.actions_dag.get_executable_actions()
            )
            octobot_commons.logging.get_logger(self.__class__.__name__).info(f"Running automation actions: {selected_actions}")
            executed_actions = await automation_job.run()
            self.after_execution_state = automation_job.automation_state
            post_execution_state_dump = automation_job.dump()
            next_actions_description, has_next_actions = self.get_next_actions_description(post_execution_state_dump)
            self.result.processed_actions = executed_actions
            self.result.next_actions_description = next_actions_description
            self.result.has_next_actions = has_next_actions
            self.result.actions_dag = automation_job.automation_state.automation.actions_dag
            self.result.should_stop = automation_job.automation_state.automation.post_actions.stop_automation

    def get_next_actions_description(
        self, post_execution_state: dict
    ) -> tuple[typing.Optional[OctoBotActionsJobDescription], bool]:
        automation = self.after_execution_state.automation
        next_actions_description = OctoBotActionsJobDescription(
            state=post_execution_state,
            auth_details=self.description.auth_details,
        )
        has_next_actions = bool(automation.actions_dag.get_executable_actions())
        if not has_next_actions and (pending_actions := automation.actions_dag.get_pending_actions()):
            raise errors.WorkflowDAGDependenciesError(
                f"Automation {automation.metadata.automation_id}: actions DAG dependencies issue: "
                f"no executable actions while there are still "
                f"{len(pending_actions)} pending actions: {pending_actions}"
            )
        return next_actions_description, has_next_actions

    def __repr__(self) -> str:
        parsed_state = octobot_flow.entities.AutomationState.from_dict(self.description.state)
        automation_repr = str(parsed_state.automation) if parsed_state.automation else "No automation"
        return f"OctoBotActionsJob with automation:\n- {automation_repr}"
