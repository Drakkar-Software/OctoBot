#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
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

"""End-to-end product-signals storage via server get_data/put_data callbacks.

Mirrors node_api wiring (set_data_callbacks + build_default_sync_app) so
append-only plaintext documents with dict ``data`` round-trip through the
opaque filesystem store.
"""

import httpx
import mock
import pytest
from fastapi import FastAPI

from starfish_sdk import StarfishClient

import octobot_commons.user_root_folder_provider as user_root_folder_provider
import octobot_sync.auth as auth
import octobot_sync.client as sync_client
import octobot_sync.constants as constants
import octobot_sync.server as sync_server
import octobot_sync.sync.collections as sync_collections

# Well-known test key (Anvil account #1).
_PRIV = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"

_STRATEGY_ID = "fc7982e2-cfbf-41ba-8f5a-38045b27883a"
_VERSION = "1.0.0"


def _signal_payload(updated_at: float) -> dict:
    return {
        "strategy_id": _STRATEGY_ID,
        "account": {"updated_at": updated_at},
    }


def _push_path() -> str:
    return f"/v1/push/products/{_STRATEGY_ID}/{_VERSION}/signals"


def _pull_path() -> str:
    return f"/v1/pull/products/{_STRATEGY_ID}/{_VERSION}/signals"


@pytest.fixture
def callback_sync_app(tmp_path):
    original_get = sync_server._get_data
    original_put = sync_server._put_data
    original_opaque = sync_server._opaque_store
    sync_server.set_data_callbacks(sync_server.get_data, sync_server.put_data)
    with mock.patch.object(
        user_root_folder_provider,
        "get_user_root_folder",
        return_value=str(tmp_path),
    ):
        inner = sync_server.build_default_sync_app(
            sync_config=sync_collections.DEFAULT_SYNC_CONFIG,
        )
        root = FastAPI()
        root.mount("/sync", inner)
        yield root
    sync_server._get_data = original_get
    sync_server._put_data = original_put
    sync_server._opaque_store = original_opaque


@pytest.fixture
async def starfish_http_client(callback_sync_app):
    http_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=callback_sync_app),
        base_url="http://test/sync",
    )
    yield http_client
    await http_client.aclose()


@pytest.fixture
def starfish_client(starfish_http_client):
    cap_provider = auth.WalletCapProvider(_PRIV)
    return StarfishClient(
        base_url="http://test/sync",
        cap_provider=cap_provider,
        namespace=constants.SYNC_NAMESPACE,
        client=starfish_http_client,
    )


@pytest.mark.asyncio
async def test_append_signals_roundtrip_via_server_callbacks(starfish_client):
    first_signal = _signal_payload(1.0)
    second_signal = _signal_payload(2.0)
    await sync_client.append_payload(
        starfish_client,
        push_path=_push_path(),
        payload=first_signal,
        timestamp=1000,
    )
    await sync_client.append_payload(
        starfish_client,
        push_path=_push_path(),
        payload=second_signal,
        timestamp=2000,
    )
    items = await starfish_client.pull(_pull_path(), append_field="items", full=True)
    payloads = [
        element["data"] if isinstance(element, dict) and "data" in element else element
        for element in items
    ]
    assert first_signal in payloads
    assert second_signal in payloads
