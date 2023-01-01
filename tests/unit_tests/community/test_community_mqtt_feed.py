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
import pytest
import pytest_asyncio
import mock
import uuid
import json
import zlib
import gmqtt

import octobot.community as community
import octobot.constants as constants
import octobot_commons.enums as commons_enums

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

FEED_URL = "x.y.z"
TOKEN = "acb1"
NAME = "name_a"


def _build_message(value, identifier):
    return {
        commons_enums.CommunityFeedAttrs.CHANNEL_TYPE.value: commons_enums.CommunityChannelTypes.SIGNAL.value,
        commons_enums.CommunityFeedAttrs.VERSION.value: constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION,
        commons_enums.CommunityFeedAttrs.VALUE.value: value,
        commons_enums.CommunityFeedAttrs.ID.value: identifier,
    }


def _zipped_message(value):
    return zlib.compress(
        json.dumps(value).encode()
    )


@pytest_asyncio.fixture
async def authenticator():
    community.IdentifiersProvider.use_production()
    auth = community.CommunityAuthentication(None, None)
    auth._auth_token = TOKEN
    auth.refresh_token = TOKEN
    auth._expire_at = 11
    return auth


@pytest_asyncio.fixture
async def connected_community_feed(authenticator):
    feed = None
    try:
        feed = community.CommunityMQTTFeed(FEED_URL, authenticator)
        feed.INIT_TIMEOUT = 1
        with mock.patch.object(authenticator.user_account, "get_selected_bot_device_uuid", mock.Mock(return_value=TOKEN)) \
                as get_selected_bot_device_uuid_mock, \
             mock.patch.object(authenticator.user_account, "get_selected_bot_device_name", mock.Mock(return_value=NAME)
                               ) as _get_selected_bot_device_uuid_mock, \
             mock.patch.object(feed, "_subscribe", mock.Mock()) as _subscribe_mock, \
             mock.patch.object(gmqtt.Client, "connect", mock.AsyncMock()) as _connect_mock:
            await feed.register_feed_callback(commons_enums.CommunityChannelTypes.SIGNAL, mock.AsyncMock())
            _subscribe_mock.assert_called_once_with((f"{commons_enums.CommunityChannelTypes.SIGNAL.value}/None", ))
            await feed.start()
            get_selected_bot_device_uuid_mock.assert_called_once()
            _connect_mock.assert_called_once_with(FEED_URL, feed.mqtt_broker_port, version=feed.MQTT_VERSION)
            yield feed
    finally:
        if feed is not None:
            await feed.stop()
            if feed._mqtt_client is not None and not feed._mqtt_client._resend_task.done():
                feed._mqtt_client._resend_task.cancel()


async def test_start_and_connect(connected_community_feed):
    # connected_community_feed already called _connect, check that everything has been set
    assert isinstance(connected_community_feed._mqtt_client, gmqtt.Client)
    assert connected_community_feed._mqtt_client._config["reconnect_retries"] == \
           connected_community_feed.DISABLE_RECONNECT_VALUE
    assert connected_community_feed._mqtt_client.on_connect == connected_community_feed._on_connect
    assert connected_community_feed._mqtt_client.on_message == connected_community_feed._on_message
    assert connected_community_feed._mqtt_client.on_disconnect == connected_community_feed._on_disconnect
    assert connected_community_feed._mqtt_client.on_subscribe == connected_community_feed._on_subscribe
    assert connected_community_feed._mqtt_client._username == TOKEN.encode()


async def test_stop(connected_community_feed):
    connected_community_feed._reconnect_task = None
    with mock.patch.object(connected_community_feed, "_stop_mqtt_client", mock.AsyncMock()) as _stop_mqtt_client_mock:
        await connected_community_feed.stop()
        _stop_mqtt_client_mock.assert_called_once()

        _stop_mqtt_client_mock.reset_mock()
        connected_community_feed._reconnect_task = mock.Mock(done=mock.Mock(return_value=True), cancel=mock.Mock())
        await connected_community_feed.stop()
        _stop_mqtt_client_mock.assert_called_once()
        connected_community_feed._reconnect_task.done.assert_called_once()
        connected_community_feed._reconnect_task.cancel.assert_not_called()

        _stop_mqtt_client_mock.reset_mock()
        connected_community_feed._reconnect_task = mock.Mock(done=mock.Mock(return_value=False), cancel=mock.Mock())
        await connected_community_feed.stop()
        _stop_mqtt_client_mock.assert_called_once()
        connected_community_feed._reconnect_task.done.assert_called_once()
        connected_community_feed._reconnect_task.cancel.assert_called_once()


async def test_register_feed_callback(connected_community_feed):
    # TODO
    pass


async def test_on_message(connected_community_feed):
    client = mock.Mock(client_id="1")
    topic = "topic"
    connected_community_feed.feed_callbacks["topic"] = [mock.AsyncMock(), mock.AsyncMock()]

    message = _build_message("hello", "1")
    # from topic
    await connected_community_feed._on_message(client, "other_topic", _zipped_message(message), 1, {})
    assert all(cb.assert_not_called() is None for cb in connected_community_feed.feed_callbacks["topic"])

    message = _build_message("hello", "2")
    # call callbacks
    await connected_community_feed._on_message(client, topic, _zipped_message(message), 1, {})
    assert all(cb.assert_called_once_with(message) is None for cb in connected_community_feed.feed_callbacks["topic"])

    # already processed message
    connected_community_feed.feed_callbacks["topic"][0].reset_mock()
    connected_community_feed.feed_callbacks["topic"][1].reset_mock()
    await connected_community_feed._on_message(client, topic, _zipped_message(message), 1, {})
    assert all(cb.assert_not_called() is None for cb in connected_community_feed.feed_callbacks["topic"])


async def test_send(connected_community_feed):
    with mock.patch.object(connected_community_feed._mqtt_client, "publish", mock.Mock()) as publish_mock, \
         mock.patch.object(uuid, "uuid4", mock.Mock(return_value="uuid41")) as uuid4_mock:
        await connected_community_feed.send("hello", commons_enums.CommunityChannelTypes.SIGNAL, "x")
        publish_mock.assert_called_once_with(
            f"{commons_enums.CommunityChannelTypes.SIGNAL.value}/x",
            zlib.compress(json.dumps({
                commons_enums.CommunityFeedAttrs.CHANNEL_TYPE.value: commons_enums.CommunityChannelTypes.SIGNAL.value,
                commons_enums.CommunityFeedAttrs.VERSION.value: constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION,
                commons_enums.CommunityFeedAttrs.VALUE.value: "hello",
                commons_enums.CommunityFeedAttrs.ID.value: "uuid41",  # assign unique id to each message
            }).encode()),
            qos=connected_community_feed.default_QOS
        )
        uuid4_mock.assert_called_once()
