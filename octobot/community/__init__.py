#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from octobot.community.analysis import (
    CommunityFields,
    CommunityManager,
    get_community_metrics,
    get_current_octobots_stats,
    can_read_metrics,
)

from octobot.community import analysis
from octobot.community import configuration
from octobot.community import authentication
from octobot.community import tentacles_packages
from octobot.community import supports
from octobot.community import errors_upload

from octobot.community.authentication import (
    CommunityAuthentication,
)

from octobot.community.configuration import (
    CommunityConfiguration,
    ConfigurationSynchronizer,
)

from octobot.community.errors_upload import (
    register_error_uploader,
    Error,
    ErrorsUploader,
)

from octobot.community.supports import (
    CommunitySupports,
    CommunityDonation,
)

from octobot.community.tentacles_packages import (
    CommunityTentaclesPackage,
)

__all__ = [
    "CommunityFields",
    "get_community_metrics",
    "get_current_octobots_stats",
    "can_read_metrics",
    "CommunityManager",
    "CommunityAuthentication",
    "CommunityTentaclesPackage",
    "CommunitySupports",
    "CommunityDonation",
    "CommunityConfiguration",
    "ConfigurationSynchronizer",
    "register_error_uploader",
    "Error",
    "ErrorsUploader",
]
