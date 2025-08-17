# pylint: disable=E0711, E0702
#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
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

import octobot.community.models.community_supports as community_supports
import octobot.community.errors as errors
import octobot.community.supabase_backend.enums as backend_enums


class CommunityUserAccount:
    USER_DATA_CONTENT = "content"
    BOT_DEVICE = "device"
    BOT_DEPLOYMENT = "bot_deployment"
    FILLED_FORMS = "filledForms"
    NO_SELECTED_BOT_DESC = "No selected bot. Please select a bot to enable your community features."
    HOSTING_ENABLED = "hosting_enabled"

    def __init__(self):
        self.bot_id = None
        self.supports = community_supports.CommunitySupports()
        self.community_package_urls: list[str] = []
        self.owned_packages: list[str] = []
        self.has_pending_packages_to_install = False

        self.last_email_address_confirm_code_email_content: typing.Optional[str] = None

        self._profile_raw_data = None
        self._selected_bot_raw_data = None
        self._all_user_bots_raw_data = []

    def has_user_data(self):
        return self._profile_raw_data is not None

    def has_selected_bot_data(self):
        return self._selected_bot_raw_data is not None

    def get_email(self):
        return self._profile_raw_data[backend_enums.UserKeys.EMAIL.value]

    def get_user_id(self):
        return self._profile_raw_data[backend_enums.UserKeys.ID.value]

    def get_has_donated(self):
        return self._get_user_data_metadata().get("has_donated", False)

    def get_filled_forms_ids(self):
        return self._get_user_data_metadata().get(self.FILLED_FORMS, [])

    def is_hosting_enabled(self):
        return self._get_user_data_metadata().get(self.HOSTING_ENABLED, False)

    def get_all_user_bots_raw_data(self):
        return self._all_user_bots_raw_data

    def get_selected_bot_raw_data(self, raise_on_missing=False):
        if raise_on_missing:
            self._ensure_selected_bot_data()
        return self._selected_bot_raw_data

    def is_self_hosted(self, bot):
        return self._get_bot_deployment(bot).get(
            backend_enums.BotDeploymentKeys.TYPE.value, backend_enums.DeploymentTypes.SELF_HOSTED.value
        ) == backend_enums.DeploymentTypes.SELF_HOSTED.value

    def is_archived(self, bot):
        return self._get_bot_deployment(bot).get(
            backend_enums.BotDeploymentKeys.STATUS.value
        ) == backend_enums.BotDeploymentStatus.ARCHIVED.value

    def get_selected_bot_deployment_id(self):
        return self.get_bot_deployment_value(backend_enums.BotDeploymentKeys.ID)

    def get_bot_deployment_status(self) -> (str, str):
        deployment = self._get_bot_deployment(self._selected_bot_raw_data)
        return (
            deployment[backend_enums.BotDeploymentKeys.STATUS.value],
            deployment[backend_enums.BotDeploymentKeys.DESIRED_STATUS.value]
        )

    def get_bot_deployment_value(self, key: backend_enums.BotDeploymentKeys):
        return self._get_bot_deployment(self._selected_bot_raw_data)[key.value]

    def get_bot_deployment_url(self, deployment_url_data):
        return deployment_url_data[backend_enums.BotDeploymentURLKeys.URL.value]

    @staticmethod
    def get_bot_id(bot):
        return bot[backend_enums.BotKeys.ID.value]

    @staticmethod
    def get_bot_name_or_id(bot):
        return bot[backend_enums.BotKeys.NAME.value]

    def get_selected_bot_current_portfolio_id(self):
        return self._selected_bot_raw_data[backend_enums.BotKeys.CURRENT_PORTFOLIO_ID.value]

    def get_selected_bot_current_config_id(self):
        return self._selected_bot_raw_data[backend_enums.BotKeys.CURRENT_CONFIG_ID.value]

    def set_profile_raw_data(self, profile_raw_data):
        self._profile_raw_data = profile_raw_data

    def set_selected_bot_raw_data(self, selected_bot_raw_data):
        self._selected_bot_raw_data = selected_bot_raw_data

    def set_selected_bot_device_raw_data(self, bot_raw_data_with_device):
        device_data = bot_raw_data_with_device[self.BOT_DEVICE]
        if device_data is None:
            raise errors.NoBotDeviceError("No device associated to the select bot")
        self._selected_bot_raw_data[self.BOT_DEVICE] = device_data

    def set_all_user_bots_raw_data(self, all_user_bots_raw_data):
        self._all_user_bots_raw_data = all_user_bots_raw_data

    def _get_user_data_content(self):
        return self._profile_raw_data[self.USER_DATA_CONTENT]

    def _get_user_data_metadata(self):
        return self._profile_raw_data.get(backend_enums.UserKeys.USER_METADATA.value, {})

    def _get_bot_deployment(self, bot):
        if bot is None:
            raise errors.BotError(self.NO_SELECTED_BOT_DESC)
        return bot.get(self.BOT_DEPLOYMENT) or {}

    def _ensure_selected_bot_data(self):
        if self._selected_bot_raw_data is None:
            raise errors.BotError(self.NO_SELECTED_BOT_DESC)

    def ensure_selected_bot_id(self):
        if self.bot_id is None:
            raise errors.BotError("No selected bot")

    def get_support_role(self):
        try:
            if self.get_has_donated():
                return community_supports.CommunitySupports.OCTOBOT_DONOR_ROLE
        except KeyError:
            pass
        return community_supports.CommunitySupports.DEFAULT_SUPPORT_ROLE

    def flush_bot_details(self):
        self.bot_id = None
        self._selected_bot_raw_data = None
        self._all_user_bots_raw_data = []

    def flush(self):
        self.supports = community_supports.CommunitySupports()
        self._profile_raw_data = None
        self.flush_bot_details()
