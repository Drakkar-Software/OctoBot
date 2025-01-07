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
import json
import pytest

from additional_tests.supabase_backend_tests import admin_client


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_upload_asset(admin_client):
    asset_content = json.dumps({"test_upload_asset_content": 1}).encode()
    asset_name = "test_upload_asset"
    asset_bucket = "product-images"
    await admin_client.remove_asset(asset_bucket, asset_name)   # remove asset if exists
    uploaded_asset_path = await admin_client.upload_asset(asset_bucket, asset_name, asset_content)

    assets = await admin_client.list_assets(asset_bucket)
    asset_by_name = {
        asset["name"]: asset
        for asset in assets
    }
    assert uploaded_asset_path in asset_by_name
    assert asset_by_name[uploaded_asset_path]["name"] == asset_name

    await admin_client.remove_asset(asset_bucket, asset_name)

    assets = await admin_client.list_assets(asset_bucket)
    asset_by_name = {
        asset["name"]: asset
        for asset in assets
    }
    # asset is removed
    assert uploaded_asset_path not in asset_by_name
