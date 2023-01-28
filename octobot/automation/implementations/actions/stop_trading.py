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
import octobot_commons.constants as commons_constants
import octobot_services.interfaces.util as interfaces_util
import octobot.automation.implementations.actions.cancel_open_orders as cancel_open_orders


class StopTrading(cancel_open_orders.CancelOpenOrders):
    PROFILE_ID = commons_constants.DEFAULT_PROFILE  # non trading profile

    async def process(self):
        # cancel all open orders
        await super().process()
        # select non trading profile
        config = interfaces_util.get_edited_config(dict_only=False)
        config.select_profile(self.PROFILE_ID)
        config.save()
        # reboot
        interfaces_util.get_bot_api().restart_bot()

    @staticmethod
    def get_description() -> str:
        return "Cancel all OctoBot-managed open orders on each exchange, switch to the Non-Trading profile " \
               "and restart OctoBot."
