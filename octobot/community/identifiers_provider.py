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
import octobot.constants as constants
import octobot.enums as enums
import octobot_commons.logging as logging
import octobot_commons.configuration as configuration


class IdentifiersProvider:
    ENABLED_ENVIRONMENT: str = None
    COMMUNITY_LANDING_URL: str = None
    COMMUNITY_API_URL: str = None
    COMMUNITY_URL: str = None
    FRONTEND_PASSWORD_RECOVER_URL: str = None
    BACKEND_URL: str = None
    BACKEND_KEY: str = None

    @staticmethod
    def use_production():
        IdentifiersProvider.COMMUNITY_URL = constants.OCTOBOT_COMMUNITY_URL
        IdentifiersProvider.COMMUNITY_LANDING_URL = constants.OCTOBOT_COMMUNITY_LANDING_URL
        IdentifiersProvider.COMMUNITY_API_URL = constants.OCTOBOT_COMMUNITY_API_URL
        IdentifiersProvider.FRONTEND_PASSWORD_RECOVER_URL = constants.OCTOBOT_COMMUNITY_RECOVER_PASSWORD_URL
        IdentifiersProvider.BACKEND_URL = constants.COMMUNITY_BACKEND_URL
        IdentifiersProvider.BACKEND_KEY = constants.COMMUNITY_BACKEND_KEY
        IdentifiersProvider._register_environment(enums.CommunityEnvironments.Production)

    @staticmethod
    def use_staging():
        IdentifiersProvider.COMMUNITY_URL = constants.STAGING_OCTOBOT_COMMUNITY_URL
        IdentifiersProvider.COMMUNITY_LANDING_URL = constants.STAGING_OCTOBOT_COMMUNITY_LANDING_URL
        IdentifiersProvider.COMMUNITY_API_URL = constants.STAGING_OCTOBOT_COMMUNITY_API_URL
        IdentifiersProvider.FRONTEND_PASSWORD_RECOVER_URL = constants.STAGING_COMMUNITY_RECOVER_PASSWORD_URL
        IdentifiersProvider.BACKEND_URL = constants.STAGING_COMMUNITY_BACKEND_URL
        IdentifiersProvider.BACKEND_KEY = constants.STAGING_COMMUNITY_BACKEND_KEY
        IdentifiersProvider._register_environment(enums.CommunityEnvironments.Staging)

    @staticmethod
    def _register_environment(env):
        if IdentifiersProvider.ENABLED_ENVIRONMENT != env:
            logging.get_logger(IdentifiersProvider.__name__).debug(f"Using {env.value} Community environment.")
        IdentifiersProvider.ENABLED_ENVIRONMENT = env

    @staticmethod
    def use_default():
        if constants.USE_BETA_EARLY_ACCESS:
            IdentifiersProvider.use_staging()
        else:
            IdentifiersProvider.use_production()

    @staticmethod
    def is_staging_environment_enabled(config: dict):
        try:
            env = config[constants.CONFIG_COMMUNITY][constants.CONFIG_COMMUNITY_ENVIRONMENT]
            return enums.CommunityEnvironments(env) is enums.CommunityEnvironments.Staging
        except (KeyError, ValueError):
            return False

    @staticmethod
    def use_environment_from_config(config: configuration.Configuration):
        if IdentifiersProvider.is_staging_environment_enabled(config.config):
            IdentifiersProvider.use_staging()
        else:
            IdentifiersProvider.use_default()
