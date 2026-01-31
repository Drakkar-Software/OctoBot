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

try:
    import mini_octobot
    import mini_octobot.environment
    import mini_octobot.parsers
    # Requires mini_octobot import and importable tentacles folder

    # ensure environment is initialized
    mini_octobot.environment.initialize_environment(True)

except ImportError:
    logging.getLogger("octobot_node.scheduler.octobot_lib").warning("OctoBot is not installed, OctoBot actions will not be available")
    # mocks to allow import
    class mini_octobot_mock:
        class BotActionDetails:
            def from_dict(self, *args, **kwargs):
                raise NotImplementedError("BotActionDetails.from_dict is not implemented")
        class SingleBotActionsJob:
            def __init__(self, *args, **kwargs):
                raise NotImplementedError("SingleBotActionsJob.__init__ is not implemented")
            async def __aenter__(self):
                raise NotImplementedError("SingleBotActionsJob.__aenter__ is not implemented")
            async def __aexit__(self, *args, **kwargs):
                raise NotImplementedError("SingleBotActionsJob.__aexit__ is not implemented")
        class parsers:
            class BotActionBundleParser:
                def __init__(self, *args, **kwargs):
                    raise NotImplementedError("BotActionBundleParser.__init__ is not implemented")
                def parse(self, *args, **kwargs):
                    raise NotImplementedError("BotActionBundleParser.parse is not implemented")
    mini_octobot = mini_octobot_mock()


@dataclasses.dataclass
class OctoBotActionsJobDescription(octobot_commons.dataclasses.MinimizableDataclass):
    state: dict = dataclasses.field(default_factory=dict)
    auth_details: dict = dataclasses.field(default_factory=dict)
    params: dict = dataclasses.field(default_factory=dict)
    immediate_actions: list[mini_octobot.BotActionDetails] = dataclasses.field(default_factory=list)
    pending_actions: list[list[mini_octobot.BotActionDetails]] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if self.immediate_actions and isinstance(self.immediate_actions[0], dict):
            self.immediate_actions = [
                mini_octobot.BotActionDetails.from_dict(action) for action in self.immediate_actions
            ]
        if self.pending_actions and self.pending_actions[0] and isinstance(self.pending_actions[0][0], dict):
            self.pending_actions = [
                [mini_octobot.BotActionDetails.from_dict(action) for action in bundle] 
                for bundle in self.pending_actions
            ]
        if self.params:
            if self.immediate_actions or self.pending_actions:
                raise ValueError("adding extra actions to a task is not yet supported")
            self._parse_actions_plan(self.params)

    def _parse_actions_plan(self, params: dict) -> None:
        action_bundles: list[list[mini_octobot.BotActionDetails]] = mini_octobot.parsers.BotActionBundleParser(params).parse()
        if not action_bundles:
            raise ValueError("No action bundles found in params")
        self.immediate_actions = action_bundles[0]
        self.pending_actions = action_bundles[1:]

    def get_next_execution_time(self) -> float:
        return min(
            bot["execution"]["current_execution"]["scheduled_to"]
            for bot in self.state["bots"]
        )


@dataclasses.dataclass
class OctoBotActionsJobResult:
    processed_actions: list[mini_octobot.BotActionDetails]
    next_actions_description: typing.Optional[OctoBotActionsJobDescription] = None

    def get_created_orders(self) -> list[dict]:
        if self.processed_actions is None:
            raise ValueError("No bot actions were executed yet")
        order_lists = [
            action.result.get("orders", [])
            for action in self.processed_actions
            if action.result
        ]
        return list_util.flatten_list(order_lists) if order_lists else []
    
    def get_deposit_and_withdrawal_details(self) -> list[dict]:
        if self.processed_actions is None:
            raise ValueError("No bot actions were executed yet")
        withdrawal_lists = [
            action.result
            for action in self.processed_actions
            if action.result and isinstance(action.result, dict) and "network" in action.result
        ]
        return withdrawal_lists


class OctoBotActionsJob:
    def __init__(self, description: str):
        parsed_description = self._parse_description(description)
        self.description: OctoBotActionsJobDescription = OctoBotActionsJobDescription.from_dict(
            parsed_description
        )
        self.after_execution_state = None

    def _parse_description(self, description: str) -> dict:
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
        selected_actions = self.description.immediate_actions
        async with mini_octobot.SingleBotActionsJob(
            self.description.state, self.description.auth_details, selected_actions
        ) as single_bot_actions_job:
            logging.getLogger(self.__class__.__name__).info(f"Running single bot actions job actions: {selected_actions}")
            await single_bot_actions_job.run()
            self.after_execution_state = single_bot_actions_job.exchange_account_details
            post_execution_state_dump = single_bot_actions_job.dump()
            return OctoBotActionsJobResult(
                processed_actions=single_bot_actions_job.bot_actions,
                next_actions_description=self.get_next_actions_description(post_execution_state_dump)
            )

    def get_next_actions_description(
        self, post_execution_state: dict
    ) -> typing.Optional[OctoBotActionsJobDescription]:
        if not self.description.pending_actions:
            # completed all actions
            return None
        return OctoBotActionsJobDescription(
            state=post_execution_state,
            auth_details=self.description.auth_details,
            # next immediate actions are the first remaining pending actions
            immediate_actions=self.description.pending_actions[0],
            # next pending actions are the remaining pending actions
            pending_actions=self.description.pending_actions[1:]
        )
