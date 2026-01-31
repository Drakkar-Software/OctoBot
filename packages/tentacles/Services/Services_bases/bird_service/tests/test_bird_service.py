#  Drakkar-Software OctoBot-Tentacles
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
import asyncio
import logging

import pytest

from tentacles.Services.Services_bases.bird_service import BirdService

import octobot_services.constants as services_constants

# Skip entire module if bird CLI is not installed
_bird_available = BirdService.is_bird_available("bird")
pytestmark = pytest.mark.skipif(
    not _bird_available,
    reason="bird CLI not found or not executable",
)


def _minimal_config(cli_path: str = "bird", account: str = ""):
    return {
        services_constants.CONFIG_CATEGORY_SERVICES: {
            services_constants.CONFIG_BIRD: {
                services_constants.CONFIG_BIRD_CLI_PATH: cli_path,
                services_constants.CONFIG_BIRD_ACCOUNT: account,
            }
        }
    }


@pytest.fixture
def bird_service():
    """Service with prepare() run and account set from whoami (so user data is available)."""
    service = BirdService()
    service.config = _minimal_config()
    service.logger = logging.getLogger("BirdService.test")
    asyncio.run(service.prepare())
    return service


@pytest.mark.asyncio
async def test_prepare(bird_service):
    msg, healthy = bird_service.get_successful_startup_message()
    assert isinstance(msg, str)
    assert isinstance(healthy, bool)


@pytest.mark.asyncio
async def test_whoami(bird_service):
    out = await bird_service.whoami()
    assert isinstance(out, str)


@pytest.mark.asyncio
async def test_check(bird_service):
    out = await bird_service.check()
    assert isinstance(out, str)


@pytest.mark.asyncio
async def test_read_tweet(bird_service):
    out = await bird_service.read_tweet("20")
    assert out is None or hasattr(out, "id")


@pytest.mark.asyncio
async def test_get_timeline(bird_service):
    out = await bird_service.get_timeline(limit=2)
    assert out, "expected non-empty list"


@pytest.mark.asyncio
async def test_get_thread(bird_service):
    out = await bird_service.get_thread("20", max_pages=1)
    assert out, "expected non-empty list"


@pytest.mark.asyncio
async def test_get_replies(bird_service):
    out = await bird_service.get_replies("20", limit=2)
    assert out, "expected non-empty list"


@pytest.mark.asyncio
async def test_search_tweets(bird_service):
    out = await bird_service.search_tweets("octobot", limit=2)
    assert out, "expected non-empty list"


@pytest.mark.asyncio
async def test_get_mentions(bird_service):
    out = await bird_service.get_mentions(limit=2)
    assert isinstance(out, list)  # empty when no mentions


@pytest.mark.asyncio
async def test_get_user_posts(bird_service):
    out = await bird_service.get_user_posts(limit=2)
    assert isinstance(out, list)  # empty when no account or no posts


@pytest.mark.asyncio
async def test_get_user_replies(bird_service):
    out = await bird_service.get_user_replies(limit=2)
    assert isinstance(out, list)  # empty when no account or no replies


@pytest.mark.asyncio
async def test_scroll_user_posts(bird_service):
    out = await bird_service.scroll_user_posts(max_pages=1)
    assert isinstance(out, dict)
    assert "tweets" in out
    assert "next_cursor" in out
    assert isinstance(out["tweets"], list)


@pytest.mark.asyncio
async def test_scroll_timeline(bird_service):
    out = await bird_service.scroll_timeline(max_pages=1)
    assert isinstance(out, dict)
    assert "tweets" in out
    assert "next_cursor" in out


@pytest.mark.asyncio
async def test_scroll_search(bird_service):
    out = await bird_service.scroll_search("test", max_pages=1)
    assert isinstance(out, dict)
    assert "tweets" in out
    assert "next_cursor" in out


@pytest.mark.asyncio
async def test_get_bookmarks(bird_service):
    out = await bird_service.get_bookmarks(limit=2)
    assert out, "expected non-empty list"


@pytest.mark.asyncio
async def test_get_likes(bird_service):
    out = await bird_service.get_likes(limit=2)
    assert out, "expected non-empty list"


@pytest.mark.asyncio
async def test_get_news(bird_service):
    out = await bird_service.get_news(limit=2)
    assert out, "expected non-empty list"


@pytest.mark.asyncio
async def test_get_list_timeline(bird_service):
    out = await bird_service.get_list_timeline("1", limit=2)
    assert isinstance(out, list)  # empty when list id invalid or list empty


@pytest.mark.asyncio
async def test_get_following(bird_service):
    out = await bird_service.get_following(limit=2)
    assert out, "expected non-empty list"


@pytest.mark.asyncio
async def test_get_followers(bird_service):
    out = await bird_service.get_followers(limit=2)
    assert out, "expected non-empty list"


@pytest.mark.asyncio
async def test_get_user_about(bird_service):
    out = await bird_service.get_user_about("@test")
    assert out is None or isinstance(out, dict)


def test_build_tweet_url():
    out = BirdService.build_tweet_url(text="hello")
    assert isinstance(out, str)
    assert "twitter.com" in out
    assert "intent/tweet" in out


def test_build_tweet_url_empty():
    out = BirdService.build_tweet_url()
    assert isinstance(out, str)
    assert out == "https://twitter.com/intent/tweet"


def test_build_reply_url():
    out = BirdService.build_reply_url("123", text="reply")
    assert isinstance(out, str)
    assert "twitter.com" in out
    assert "in_reply_to=123" in out


def test_get_type(bird_service):
    out = bird_service.get_type()
    assert out == services_constants.CONFIG_BIRD


def test_get_fields_description(bird_service):
    out = bird_service.get_fields_description()
    assert isinstance(out, dict)


def test_get_default_value(bird_service):
    out = bird_service.get_default_value()
    assert isinstance(out, dict)


def test_get_read_only_info(bird_service):
    out = bird_service.get_read_only_info()
    assert out, "expected non-empty list (account set from whoami after prepare)"
