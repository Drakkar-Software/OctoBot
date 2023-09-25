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
import contextlib
import mock
import pytest
import pytest_asyncio
import sentry_sdk

import octobot.community.errors_upload.sentry_aiohttp_transport
import octobot_commons.logging
import octobot_commons.asyncio_tools


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


SENTRY_CONFIG = {
    "enabled": False
}


@pytest_asyncio.fixture
async def sentry_init():
    handle = None
    SENTRY_CONFIG["enabled"] = True
    try:
        def _before_send_callback(event: dict, hint: dict):
            # disable after test to avoid spamming in other tests in case client.close does not work
            if SENTRY_CONFIG["enabled"]:
                return event
            return None

        handle = sentry_sdk.init(
            dsn="https://9ad6367a0c2a4b7d8a3014ab87a2d96e@plop.com/1",

            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            # We recommend adjusting this value in production.
            traces_sample_rate=1.0,

            before_send=_before_send_callback,
            transport=octobot.community.errors_upload.sentry_aiohttp_transport.SentryAiohttpTransport,
        )
        handle._client.transport._worker.start()
        yield handle._client.transport
    finally:
        SENTRY_CONFIG["enabled"] = False
        if handle and hasattr(handle._client.transport, "async_kill"):
            await handle._client.transport.async_kill()
        client = sentry_sdk.Hub.current.client
        if client is not None:
            client.close(timeout=0)


def _mocked_context(return_value):
    call_mock = mock.AsyncMock()

    @contextlib.asynccontextmanager
    async def _inner(*args, **kwargs):
        await call_mock(*args, **kwargs)
        yield return_value
    return _inner, call_mock


def _mocked_resp():
    return mock.Mock(
        status=200,
        headers={},
        text=mock.AsyncMock(return_value="plop")
    )


async def test_upload_error(sentry_init):
    transport = sentry_init
    patched_post, post_mock = _mocked_context(_mocked_resp())
    logger = octobot_commons.logging.get_logger(__name__)
    with mock.patch.object(transport._worker.session, "post", patched_post):
        # test with error
        logger.error("error message hello")
        post_mock.assert_not_called()
        await octobot_commons.asyncio_tools.wait_asyncio_next_cycle()
        # if post_mock is called, then the whole transport works as the aiohttp session post is called by sentry
        assert len(post_mock.mock_calls) == 1
        assert post_mock.mock_calls[0].args == ('https://plop.com/api/1/envelope/',)
        assert list(post_mock.mock_calls[0].kwargs) == ["data", "headers"]

        post_mock.reset_mock()
        # test with exception
        try:
            1/0
        except ZeroDivisionError as err:
            logger.exception(err, True, f"demo exception {err}")
        await octobot_commons.asyncio_tools.wait_asyncio_next_cycle()
        # if post_mock is called, then the whole transport works as the aiohttp session post is called by sentry
        assert len(post_mock.mock_calls) == 2   # called twice to account for error and exception log
        for call in post_mock.mock_calls:
            assert call.args == ('https://plop.com/api/1/envelope/',)
            assert list(call.kwargs) == ["data", "headers"]

        post_mock.reset_mock()
        try:
            1/0
        except ZeroDivisionError as err:
            logger.exception(err, False, f"demo exception {err}")
        await octobot_commons.asyncio_tools.wait_asyncio_next_cycle()
        # if post_mock is called, then the whole transport works as the aiohttp session post is called by sentry
        assert len(post_mock.mock_calls) == 1   # called for exception log only
        for call in post_mock.mock_calls:
            assert call.args == ('https://plop.com/api/1/envelope/',)
            assert list(call.kwargs) == ["data", "headers"]
