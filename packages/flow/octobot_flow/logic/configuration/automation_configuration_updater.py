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

import time
import copy
import typing

import octobot_commons.logging as common_logging
import octobot_commons.profiles.profile_data as profiles_import
import octobot_trading.util.test_tools.exchange_data as exchange_data_import

import octobot_flow.entities
import octobot_flow.errors


class AutomationConfigurationUpdater:
    def __init__(
        self,
        automation_state: octobot_flow.entities.AutomationState,
        action: octobot_flow.entities.ConfiguredActionDetails,
    ):
        self.automation_state: octobot_flow.entities.AutomationState = automation_state
        self.action: octobot_flow.entities.ConfiguredActionDetails = action
        self._logger: common_logging.BotLogger = common_logging.get_logger(self.__class__.__name__)

    async def update(self):
        start_time = time.time()
        try:
            automation_state_update = octobot_flow.entities.AutomationState.from_dict(
                self.action.config
            )
        except TypeError as err:
            raise octobot_flow.errors.InvalidConfigurationActionError(
                f"Invalid configuration update format: {err}. "
                f"A octobot_flow.entities.AutomationState parsable dict is expected."
            ) from err
        self._apply_automation_state_configuration_update(automation_state_update)
        self._register_execution_time(start_time)
        self._complete_execution_and_register_next_schedule_time()
        self.action.complete()

    def _apply_automation_state_configuration_update(
        self, automation_state_update: octobot_flow.entities.AutomationState
    ):
        if automation_state_update.exchange_account_details:
            updating_exchange_account_id = self._update_exchange_details(
                automation_state_update.exchange_account_details
            )
            if updating_exchange_account_id:
                self._logger.info("Resetting exchange auth details as the exchange account id has changed")
                self.automation_state.exchange_account_details.auth_details = exchange_data_import.ExchangeAuthDetails()
            else:
                self._update_auth_details(automation_state_update.exchange_account_details)
            self._update_portfolio(automation_state_update.exchange_account_details)
        self._update_automation(automation_state_update)

    def _update_exchange_details(
        self, configuration_update: octobot_flow.entities.ExchangeAccountDetails
    ) -> bool:
        exchange_data_update = profiles_import.ExchangeData().get_update(
            configuration_update.exchange_details
        )
        updating_exchange_account_id = bool(
            exchange_data_update.exchange_account_id
            and exchange_data_update.exchange_account_id != self.automation_state.exchange_account_details.exchange_details.exchange_account_id
        )
        self.automation_state.exchange_account_details.exchange_details.update(exchange_data_update)
        return updating_exchange_account_id

    def _update_auth_details(
        self, configuration_update: octobot_flow.entities.ExchangeAccountDetails
    ):
        local_auth_details = copy.deepcopy(configuration_update.auth_details)
        base_auth_details = exchange_data_import.ExchangeAuthDetails()
        local_auth_details.exchange_credential_id = None
        auth_details_update = base_auth_details.get_update(local_auth_details)
        self.automation_state.exchange_account_details.auth_details.update(auth_details_update)

    def _update_portfolio(
        self, configuration_update: octobot_flow.entities.ExchangeAccountDetails
    ):
        if self.automation_state.exchange_account_details.is_simulated():
            portfolio_update = octobot_flow.entities.ExchangeAccountPortfolio().get_update(configuration_update.portfolio)
            self.automation_state.exchange_account_details.portfolio.update(portfolio_update)

    def _update_automation(
        self, automation_state_update: octobot_flow.entities.AutomationState
    ):
        automation_update = automation_state_update.automation
        base_automation = octobot_flow.entities.AutomationDetails()
        update_result = base_automation.get_update(automation_update)
        self.automation_state.automation.update(update_result)

    def _register_execution_time(self, start_time: float):
        automation = self.automation_state.automation
        if automation.execution.previous_execution.triggered_at:
            automation.execution.current_execution.triggered_at = automation.execution.previous_execution.triggered_at
        else:
            automation.execution.current_execution.triggered_at = start_time

    def _complete_execution_and_register_next_schedule_time(self):
        self.automation_state.automation.execution.complete_execution(0)
        self._logger.info(f"Next action will trigger immediately")
