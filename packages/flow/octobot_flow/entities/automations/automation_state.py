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

import dataclasses
import typing
import decimal

import octobot_commons.dataclasses
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

import octobot_flow.entities.accounts.exchange_account_details as exchange_account_details_import
import octobot_flow.entities.automations.automation_details as automation_details_import
import octobot_flow.errors
import octobot_flow.entities.actions.action_details as action_details_import
import octobot_flow.entities.actions.actions_dag as actions_dag_import


def required_exchange_account_details(func: typing.Callable) -> typing.Callable:
    def required_exchange_account_details_wrapper(self, *args, **kwargs):
        if not self.exchange_account_details:
            raise octobot_flow.errors.NoExchangeAccountDetailsError("Exchange account details are required")
        return func(self, *args, **kwargs)
    return required_exchange_account_details_wrapper


@dataclasses.dataclass
class AutomationState(octobot_commons.dataclasses.MinimizableDataclass):
    """
    Defines the state of a single automation which is potentially associated to an exchange account.
    """
    automation: automation_details_import.AutomationDetails = dataclasses.field(default_factory=automation_details_import.AutomationDetails, repr=True)
    exchange_account_details: typing.Optional[exchange_account_details_import.ExchangeAccountDetails] = dataclasses.field(default=None, repr=True)
    priority_actions: list[action_details_import.AbstractActionDetails] = dataclasses.field(default_factory=list, repr=True)

    def update_automation_actions(self, actions: list[action_details_import.AbstractActionDetails]):
        existing_actions = self.automation.actions_dag.get_actions_by_id()
        for action in actions:
            if action.id not in existing_actions:
                self.automation.actions_dag.add_action(action)

    def has_exchange(self) -> bool:
        return bool(
            self.exchange_account_details is not None
            and self.exchange_account_details.exchange_details.internal_name
        )

    @required_exchange_account_details
    def to_minimal_exchange_data(self, _automation_id: typing.Optional[str] = None) -> exchange_data_import.ExchangeData:
        return self.exchange_account_details.to_minimal_exchange_data(
            self._get_automation_portfolio()
        )

    def _get_automation_portfolio(self) -> dict[str, dict[str, decimal.Decimal]]:
        elements = self.automation.get_exchange_account_elements(False)
        return elements.portfolio.content if elements else {}  # type: ignore

    def update_priority_actions(self, added_actions: list[action_details_import.AbstractActionDetails]):
        included_action_ids = set(
            action.id for action in self.priority_actions
        )
        self.priority_actions.extend(
            action
            for action in added_actions
            if action.id not in included_action_ids
        )

    def __post_init__(self):
        if self.automation and isinstance(self.automation, dict):
            self.automation = automation_details_import.AutomationDetails.from_dict(self.automation)
        if self.exchange_account_details and isinstance(self.exchange_account_details, dict):
            self.exchange_account_details = exchange_account_details_import.ExchangeAccountDetails.from_dict(self.exchange_account_details)
