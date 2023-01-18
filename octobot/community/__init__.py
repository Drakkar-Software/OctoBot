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

from octobot.community import errors
from octobot.community.errors import (
    RequestError,
    StatusCodeRequestError,
)
from octobot.community import identifiers_provider
from octobot.community.identifiers_provider import (
    IdentifiersProvider,
)
from octobot.community import community_user_account
from octobot.community.community_user_account import (
    CommunityUserAccount,
)
from octobot.community import community_fields
from octobot.community.community_fields import (
    CommunityFields,
)

from octobot.community import community_analysis
from octobot.community import community_manager
from octobot.community import authentication
from octobot.community import community_tentacles_package
from octobot.community import community_supports
from octobot.community import community_donation
from octobot.community import startup_info
from octobot.community import graphql_requests
from octobot.community import feeds
from octobot.community import errors_upload

from octobot.community.community_analysis import (
    get_community_metrics,
    get_current_octobots_stats,
    can_read_metrics,
)
from octobot.community.community_manager import (
    CommunityManager,
)
from octobot.community.authentication import (
    CommunityAuthentication,
)
from octobot.community.community_tentacles_package import (
    CommunityTentaclesPackage
)
from octobot.community.community_supports import (
    CommunitySupports
)
from octobot.community.community_donation import (
    CommunityDonation
)
from octobot.community.startup_info import (
    StartupInfo
)
from octobot.community.graphql_requests import (
    select_startup_info_query,
    select_bot_query,
    select_bots_query,
    create_bot_query,
    create_bot_device_query,
    update_bot_config_and_stats_query,
    select_subscribed_profiles_query,
    update_bot_trades_query,
    update_bot_portfolio_query,
)
from octobot.community.feeds import (
    AbstractFeed,
    CommunityWSFeed,
    CommunityMQTTFeed,
    community_feed_factory,
)
from octobot.community.errors_upload import (
    register_error_uploader,
    Error,
    ErrorsUploader,
)

__all__ = [
    "RequestError",
    "StatusCodeRequestError",
    "IdentifiersProvider",
    "CommunityUserAccount",
    "CommunityFields",
    "get_community_metrics",
    "get_current_octobots_stats",
    "can_read_metrics",
    "CommunityManager",
    "CommunityAuthentication",
    "CommunityTentaclesPackage",
    "CommunitySupports",
    "CommunityDonation",
    "register_error_uploader",
    "Error",
    "ErrorsUploader",
    "StartupInfo",
    "select_startup_info_query",
    "select_bot_query",
    "select_bots_query",
    "create_bot_query",
    "create_bot_device_query",
    "update_bot_config_and_stats_query",
    "select_subscribed_profiles_query",
    "update_bot_trades_query",
    "update_bot_portfolio_query",
    "AbstractFeed",
    "CommunityWSFeed",
    "CommunityMQTTFeed",
    "community_feed_factory",
]
