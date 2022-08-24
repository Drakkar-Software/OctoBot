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
import octobot.constants as constants
import octobot.enums as enums
import octobot_commons.logging as logging
import octobot_commons.configuration as configuration


class IdentifiersProvider:
    ENABLED_ENVIRONMENT = None
    COMMUNITY_URL = None
    FEED_URL = None
    BACKEND_API_URL = None
    BACKEND_AUTH_URL = None
    BACKEND_PUBLIC_TOKEN = None
    MONGO_REALM_URL = None
    MONGO_APP_ID = None
    GQL_AUTH_URL = None
    GQL_BACKEND_API_URL = None

    @staticmethod
    def use_production():
        IdentifiersProvider.COMMUNITY_URL = constants.OCTOBOT_COMMUNITY_URL
        IdentifiersProvider.FEED_URL = constants.OCTOBOT_COMMUNITY_FEED_URL
        IdentifiersProvider.BACKEND_API_URL = constants.COMMUNITY_BACKEND_API_URL
        IdentifiersProvider.BACKEND_AUTH_URL = constants.COMMUNITY_BACKEND_AUTH_URL
        IdentifiersProvider.BACKEND_PUBLIC_TOKEN = constants.COMMUNITY_BACKEND_PUBLIC_TOKEN
        IdentifiersProvider.MONGO_REALM_URL = constants.COMMUNITY_MONGO_REALM_URL
        IdentifiersProvider.MONGO_APP_ID = constants.COMMUNITY_MONGO_APP_ID
        IdentifiersProvider.GQL_AUTH_URL = constants.COMMUNITY_GQL_AUTH_URL
        IdentifiersProvider.GQL_BACKEND_API_URL = constants.COMMUNITY_GQL_BACKEND_API_URL
        IdentifiersProvider._register_environment(enums.CommunityEnvironments.Production)

    @staticmethod
    def use_staging():
        IdentifiersProvider.COMMUNITY_URL = constants.STAGING_OCTOBOT_COMMUNITY_URL
        IdentifiersProvider.FEED_URL = constants.STAGING_OCTOBOT_COMMUNITY_FEED_URL
        IdentifiersProvider.BACKEND_API_URL = constants.STAGING_COMMUNITY_BACKEND_API_URL
        IdentifiersProvider.BACKEND_AUTH_URL = constants.STAGING_COMMUNITY_BACKEND_AUTH_URL
        IdentifiersProvider.BACKEND_PUBLIC_TOKEN = constants.STAGING_COMMUNITY_BACKEND_PUBLIC_TOKEN
        IdentifiersProvider.MONGO_REALM_URL = constants.STAGING_COMMUNITY_MONGO_REALM_URL
        IdentifiersProvider.MONGO_APP_ID = constants.STAGING_COMMUNITY_MONGO_APP_ID
        IdentifiersProvider.GQL_AUTH_URL = constants.STAGING_COMMUNITY_GQL_AUTH_URL
        IdentifiersProvider.GQL_BACKEND_API_URL = constants.STAGING_COMMUNITY_GQL_BACKEND_API_URL
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
