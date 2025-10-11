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
import contextlib

import octobot.community.history_backend.clickhouse_historical_backend_client as clickhouse_historical_backend_client
import octobot.community.history_backend.iceberg_historical_backend_client as iceberg_historical_backend_client
import octobot.enums


@contextlib.asynccontextmanager
async def history_backend_client(
    backend_type: octobot.enums.CommunityHistoricalBackendType = octobot.enums.CommunityHistoricalBackendType.DEFAULT,
    **kwargs
):
    client = _create_client(backend_type, **kwargs)
    try:
        await client.open()
        yield client
    finally:
        await client.close()

def _create_client(
    backend_type: octobot.enums.CommunityHistoricalBackendType = octobot.enums.CommunityHistoricalBackendType.DEFAULT,
    **kwargs
):
    """
    Usage:
    async with history_backend_client(backend_type) as client:
        await client.xxxx()
    """
    if backend_type is octobot.enums.CommunityHistoricalBackendType.Iceberg:
        return iceberg_historical_backend_client.IcebergHistoricalBackendClient(**kwargs)
    if backend_type is octobot.enums.CommunityHistoricalBackendType.Clickhouse:
        return clickhouse_historical_backend_client.ClickhouseHistoricalBackendClient(**kwargs)
    raise NotImplementedError(f"Unsupported historical backend type: {backend_type}")
