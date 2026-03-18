#  Drakkar-Software OctoBot-Sync
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

"""Tests for app.py helpers (_create_authenticated_client)."""

import httpx
import pytest

import octobot_sync.app as sync_app
import octobot_sync.constants as constants


async def test_create_authenticated_client_no_provider():
    client = sync_app._create_authenticated_client(None)
    try:
        assert isinstance(client, httpx.AsyncClient)
        assert client._event_hooks["request"] == []
    finally:
        await client.aclose()


async def test_create_authenticated_client_with_provider():
    async def fake_provider(*, method, path, body):
        return {"X-Auth": "signed"}

    client = sync_app._create_authenticated_client(fake_provider)
    try:
        assert len(client._event_hooks["request"]) == 1
    finally:
        await client.aclose()


async def test_create_authenticated_client_signs_request():
    """Auth provider headers appear on outgoing requests."""
    captured_headers = {}

    async def fake_provider(*, method, path, body):
        return {constants.HEADER_PUBKEY: "0xTestAddr", constants.HEADER_CHAIN: "evm:1"}

    async def mock_handler(request: httpx.Request):
        captured_headers.update(dict(request.headers))
        return httpx.Response(200, json={"ok": True})

    client = sync_app._create_authenticated_client(fake_provider)
    client._transport = httpx.MockTransport(mock_handler)
    try:
        await client.get("http://example.com/test")
        assert captured_headers[constants.HEADER_PUBKEY.lower()] == "0xTestAddr"
        assert captured_headers[constants.HEADER_CHAIN.lower()] == "evm:1"
    finally:
        await client.aclose()
