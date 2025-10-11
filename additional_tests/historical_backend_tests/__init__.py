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
import dotenv
import pytest_asyncio
import os

LOADED_BACKEND_CREDS_ENV_VARIABLES = False
def _load_historical_backend_creds_env_variables_if_necessary():
    global LOADED_BACKEND_CREDS_ENV_VARIABLES
    if not LOADED_BACKEND_CREDS_ENV_VARIABLES:
        # load environment variables from .env file if exists
        dotenv_path = os.getenv("HISTORICAL_BACKEND_TESTS_DOTENV_PATH", os.path.dirname(os.path.abspath(__file__)))
        dotenv.load_dotenv(os.path.join(dotenv_path, ".env"), verbose=False)
        LOADED_BACKEND_CREDS_ENV_VARIABLES = True

# load it before octobot constants
_load_historical_backend_creds_env_variables_if_necessary()

import octobot.community
import octobot.enums


@pytest_asyncio.fixture
async def clickhouse_client():
    async with octobot.community.history_backend_client(octobot.enums.CommunityHistoricalBackendType.Clickhouse) as client:
        yield client


@pytest_asyncio.fixture
async def iceberg_client():
    async with octobot.community.history_backend_client(octobot.enums.CommunityHistoricalBackendType.Iceberg) as client:
        yield client
