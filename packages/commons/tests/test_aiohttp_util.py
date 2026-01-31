#  Drakkar-Software OctoBot-Commons
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
import contextlib
import mock
import pytest
import aiohttp
import certifi

import octobot_commons.aiohttp_util as aiohttp_util
import octobot_commons.constants as commons_constants

pytestmark = pytest.mark.asyncio


async def test_get_ssl_fallback_aiohttp_client_session():
    origin_where = certifi.where
    ok_get_mock_calls = []
    ko_get_mock = []

    @contextlib.asynccontextmanager
    async def _ok_get_mock(*args, **kwargs):
        ok_get_mock_calls.append(1)
        yield mock.Mock(status=200)

    @contextlib.asynccontextmanager
    async def _ko_get_mock(*args, **kwargs):
        ko_get_mock.append(1)
        yield mock.Mock(status=200)
        raise aiohttp.ClientConnectorCertificateError("ssl blabla", RuntimeError())

    with mock.patch.object(certifi, "where", mock.Mock(side_effect=origin_where)) as where_mock:

        # no need for certifi
        with mock.patch.object(aiohttp.ClientSession, "get", _ok_get_mock):
            session = await aiohttp_util.get_ssl_fallback_aiohttp_client_session(
                commons_constants.KNOWN_POTENTIALLY_SSL_FAILED_REQUIRED_URL
            )
            assert isinstance(session, aiohttp.ClientSession)
            assert len(ok_get_mock_calls) == 1
            ok_get_mock_calls.clear()
            assert len(ko_get_mock) == 0
            where_mock.assert_not_called()
            await session.close()

        # need for certifi
        with mock.patch.object(aiohttp.ClientSession, "get", _ko_get_mock):
            async with aiohttp_util.ssl_fallback_aiohttp_client_session(
                commons_constants.KNOWN_POTENTIALLY_SSL_FAILED_REQUIRED_URL
            ):
                assert isinstance(session, aiohttp.ClientSession)
                assert len(ok_get_mock_calls) == 0
                assert len(ko_get_mock) == 1
                where_mock.assert_called_once()


async def test_fetch_test_url_with_and_without_certify():
    base_session = aiohttp.ClientSession()
    certify_session = aiohttp_util._get_certify_aiohttp_client_session()
    try:
        async with base_session.get(commons_constants.KNOWN_POTENTIALLY_SSL_FAILED_REQUIRED_URL) as resp:
            assert resp.status < 400
            base_text = await resp.text()
            assert "DrakkarSoftware" in base_text
        async with certify_session.get(commons_constants.KNOWN_POTENTIALLY_SSL_FAILED_REQUIRED_URL) as resp:
            assert resp.status < 400
            certifi_text = await resp.text()
            assert base_text == certifi_text
    finally:
        if base_session:
            await base_session.close()
        if certify_session:
            await certify_session.close()


async def test_certify_aiohttp_client_session():
    origin_where = certifi.where

    with mock.patch.object(certifi, "where", mock.Mock(side_effect=origin_where)) as where_mock:
        async with aiohttp_util.certify_aiohttp_client_session() as session:
            assert isinstance(session, aiohttp.ClientSession)
            where_mock.assert_called_once()


async def test_counter_client_session():
    async with aiohttp_util.CounterClientSession("test") as session:
        assert isinstance(session, aiohttp.ClientSession)
        assert session.per_min.name == "test"
        assert session.per_hour.name == "test"
        assert session.per_day.name == "test"

        # ensure counters work
        async with session.get("https://ifconfig.me/", headers={"Content-Type": "application/json"}) as resp:
            assert resp.status == 200
            assert session.per_min.paths == {"[GET] /": 1}
            assert session.per_hour.paths == {"[GET] /": 1}
            assert session.per_day.paths == {"[GET] /": 1}
