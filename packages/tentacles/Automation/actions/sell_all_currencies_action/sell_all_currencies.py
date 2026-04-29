#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
import asyncio

import octobot_commons.configuration as configuration
import octobot_trading.api as trading_api
import octobot.automation.bases.abstract_action as abstract_action
import octobot.automation.bases.execution_details as execution_details


class SellAllCurrencies(abstract_action.AbstractAction):
    async def process(
        self, execution_details: execution_details.ExecutionDetails
    ) -> bool:
        exchange_managers = trading_api.get_exchange_managers_from_exchange_ids(trading_api.get_exchange_ids())
        await asyncio.gather(*(
            trading_api.sell_all_everything_for_reference_market(exchange_manager)
            for exchange_manager in exchange_managers
        ))
        return True

    @staticmethod
    def get_description() -> str:
        return "Market sell each currency for the reference market on each exchange."

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        # no config
        pass
