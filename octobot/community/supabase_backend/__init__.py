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

from octobot.community.supabase_backend import postgres_functions
from octobot.community.supabase_backend.postgres_functions import (
    PostgresFunctions,
)
from octobot.community.supabase_backend import configuration_storage
from octobot.community.supabase_backend.configuration_storage import (
    SyncConfigurationStorage,
    ASyncConfigurationStorage,
)
from octobot.community.supabase_backend import supabase_client
from octobot.community.supabase_backend.supabase_client import (
    AuthenticatedAsyncSupabaseClient,
)
from octobot.community.supabase_backend import community_supabase_client
from octobot.community.supabase_backend.community_supabase_client import (
    CommunitySupabaseClient,
)

__all__ = [
    "PostgresFunctions",
    "SyncConfigurationStorage",
    "ASyncConfigurationStorage",
    "AuthenticatedAsyncSupabaseClient",
    "CommunitySupabaseClient",
]
