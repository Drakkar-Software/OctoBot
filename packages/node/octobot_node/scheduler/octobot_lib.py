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

import octobot_commons.dataclasses

import octobot_node.scheduler.workflows_util as workflows_util

try:
    import mini_octobot
    import mini_octobot.environment
    import mini_octobot.parsers
    import mini_octobot.entities
    # Requires mini_octobot import and importable tentacles folder

    # ensure environment is initialized
    mini_octobot.environment.initialize_environment(True)


except ImportError:
    logging.getLogger("octobot_node.scheduler.octobot_lib").warning("OctoBot is not installed, OctoBot actions will not be available")


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
        if not automation_id and isinstance(to_add_actions_dag.actions[0], mini_octobot.entities.ConfiguredActionDetails) and to_add_actions_dag.actions[0].config:
            config = to_add_actions_dag.actions[0].config
            if "automation" in config:
                automation_id = config["automation"]["metadata"]["automation_id"]
        if not automation_id:
            raise ValueError("No automation id found in params")
        self._include_actions_in_automation_state(automation_id, to_add_actions_dag)

    def _include_actions_in_automation_state(self, automation_id: str, actions: "mini_octobot.ActionsDAG"):
        automation_state = mini_octobot.AutomationState.from_dict(self.state)
        if not automation_state.automation.metadata.automation_id:
            automation_state.automation = mini_octobot.entities.AutomationDetails(
                metadata=mini_octobot.entities.AutomationMetadata(
                    automation_id=automation_id,
                ),
                actions_dag=actions,
            )
        else:
            automation_state.update_automation_actions(actions.actions)
        self.state = automation_state.to_dict(include_default_values=False)

    def get_next_execution_time(self) -> float:
        return self.state["automation"]["execution"]["current_execution"]["scheduled_to"]


@dataclasses.dataclass
class OctoBotActionsJobResult:
    processed_actions: list["mini_octobot.AbstractActionDetails"]
    next_actions_description: typing.Optional[OctoBotActionsJobDescription] = None
    actions_dag: typing.Optional["mini_octobot.ActionsDAG"] = None


class OctoBotActionsJob:
    def __init__(self, description: typing.Union[str, dict]):
        parsed_description = self._parse_description(description)
        self.description: OctoBotActionsJobDescription = OctoBotActionsJobDescription.from_dict(
            parsed_description
        )
        self.after_execution_state = None

    def _parse_description(self, description: typing.Union[str, dict]) -> dict:
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
                # TMP: add a simulated portfolio to the params
                parsed_description["params"]["SIMULATED_PORTFOLIO"] = {
                    "ETH": 1,
                }
        return parsed_description

    async def run(self) -> OctoBotActionsJobResult:
        async with mini_octobot.AutomationJob(
            self.description.state, self.description.auth_details
        ) as automation_job:
            selected_actions = automation_job.automation_state.automation.actions_dag.get_executable_actions()
            logging.getLogger(self.__class__.__name__).info(f"Running automation actions: {selected_actions}")
            await automation_job.run()
            automation_job.automation_state.automation.actions_dag.update_actions_results(selected_actions)
            self.after_execution_state = automation_job.automation_state
            post_execution_state_dump = automation_job.dump()
            return OctoBotActionsJobResult(
                processed_actions=selected_actions,
                next_actions_description=self.get_next_actions_description(post_execution_state_dump),
                actions_dag=automation_job.automation_state.automation.actions_dag,
            )

    def get_next_actions_description(
        self, post_execution_state: dict
    ) -> typing.Optional[OctoBotActionsJobDescription]:
        automation = self.after_execution_state.automation
        if automation.actions_dag.get_executable_actions():
            return OctoBotActionsJobDescription(
                state=post_execution_state,
                auth_details=self.description.auth_details,
            )
        if pending_actions := automation.actions_dag.get_pending_actions():
            raise ValueError(
                f"Automation {automation.metadata.automation_id}: actions DAG dependencies issue: "
                f"no executable actions while there are still "
                f"{len(pending_actions)} pending actions: {pending_actions}"
            )
        return None

    def __repr__(self) -> str:
        parsed_state = mini_octobot.AutomationState.from_dict(self.description.state)
        automation_repr = str(parsed_state.automation) if parsed_state.automation else "No automation"
        return f"OctoBotActionsJob with automation:\n- {automation_repr}"


