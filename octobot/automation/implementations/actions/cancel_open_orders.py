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


class CancelOpenOrders(abstract_action.AbstractAction):
    async def process(self):
        exchange_managers = trading_api.get_exchange_managers_from_exchange_ids(trading_api.get_exchange_ids())
        await asyncio.gather(*(
            trading_api.cancel_all_open_orders(exchange_manager)
            for exchange_manager in exchange_managers
        ))

    @staticmethod
    def get_description() -> str:
        return "Cancel all OctoBot-managed open orders on each exchange."

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        # no config
        pass
