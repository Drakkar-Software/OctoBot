#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
import octobot.community.community_supports as community_supports
import octobot.community.errors as errors


class CommunityUserAccount:
    USER_DATA_CONTENT = "content"
    BOT_DEVICE = "device"
    NO_SELECTED_BOT_DESC = "No selected bot. Please select a bot to enable your community features."

    def __init__(self):
        self.gql_user_id = None
        self.gql_bot_id = None
        self.gql_access_token = None
        self.supports = community_supports.CommunitySupports()

        self._profile_raw_data = None
        self._selected_bot_raw_data = None
        self._all_user_bots_raw_data = []

    def has_user_data(self):
        return self._profile_raw_data is not None

    def has_selected_bot_data(self):
        return self._selected_bot_raw_data is not None

    def get_email(self):
        return self._profile_raw_data["email"]

    def get_graph_token(self):
        return self._get_user_data_content()["graph_token"]

    def get_has_donated(self):
        return self._get_user_data_content()["has_donated"]

    def get_all_user_bots_raw_data(self):
        return self._all_user_bots_raw_data

    def get_selected_bot_raw_data(self, raise_on_missing=False):
        if raise_on_missing and self._selected_bot_raw_data is None:
            raise errors.BotError(self.NO_SELECTED_BOT_DESC)
        return self._selected_bot_raw_data

    def get_selected_bot_device_uuid(self):
        try:
            return self.get_selected_bot_raw_data(raise_on_missing=True).get(self.BOT_DEVICE, {}).get("uuid", None)
        except AttributeError:
            raise errors.NoBotDeviceError("No device associated to the select bot")

    def get_selected_bot_device_name(self):
        try:
            return self.get_selected_bot_raw_data(raise_on_missing=True).get(self.BOT_DEVICE, {}).get("name", None)
        except AttributeError:
            raise errors.NoBotDeviceError("No device associated to the select bot")

    @staticmethod
    def get_bot_id(bot):
        return bot["_id"]

    @staticmethod
    def get_bot_name_or_id(bot):
        return bot["name"] or CommunityUserAccount.get_bot_id(bot)

    def set_profile_raw_data(self, profile_raw_data):
        self._profile_raw_data = profile_raw_data

    def set_selected_bot_raw_data(self, selected_bot_raw_data):
        self._selected_bot_raw_data = selected_bot_raw_data

    def set_selected_bot_device_raw_data(self, bot_raw_data_with_device):
        self._selected_bot_raw_data[self.BOT_DEVICE] = bot_raw_data_with_device[self.BOT_DEVICE]

    def set_all_user_bots_raw_data(self, all_user_bots_raw_data):
        self._all_user_bots_raw_data = all_user_bots_raw_data

    def _get_user_data_content(self):
        return self._profile_raw_data[self.USER_DATA_CONTENT]

    def flush_bot_details(self):
        self.gql_bot_id = None
        self._selected_bot_raw_data = None
        self._all_user_bots_raw_data = []

    def flush(self):
        self.gql_user_id = None
        self.gql_access_token = None
        self.supports = community_supports.CommunitySupports()
        self._profile_raw_data = None
        self.flush_bot_details()
