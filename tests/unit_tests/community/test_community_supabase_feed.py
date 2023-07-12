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

import octobot.community as community
import octobot.community.supabase_backend.enums as supabase_enums
import octobot_commons.authentication as commons_authentication
import octobot.constants as constants
import octobot_commons.enums as commons_enums

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

AUTH_URL = "https://oh.fake/auth"


def _build_message(value, identifier):
    return {
        commons_enums.CommunityFeedAttrs.CHANNEL_TYPE.value: commons_enums.CommunityChannelTypes.SIGNAL.value,
        commons_enums.CommunityFeedAttrs.VERSION.value: constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION,
        commons_enums.CommunityFeedAttrs.VALUE.value: value,
        commons_enums.CommunityFeedAttrs.ID.value: identifier,
    }


@pytest_asyncio.fixture
async def authenticated_feed():
    community.IdentifiersProvider.use_production()
    authenticator = community.CommunityAuthentication(AUTH_URL, None)
    try:
        channel_mock = mock.Mock()
        channel_mock.on=mock.Mock(return_value=channel_mock)
        channel_mock.subscribe=mock.AsyncMock(return_value=channel_mock)

        realtime_mock = mock.Mock(
            channel=mock.AsyncMock(return_value=channel_mock)
        )
        authenticator.supabase_client = mock.Mock(
            sign_in=mock.AsyncMock(),
            sign_in_with_otp_token=mock.AsyncMock(),
            sign_out=mock.Mock(),
            auth=mock.Mock(_storage_key="_storage_key"),
            close=mock.AsyncMock(),
            realtime=realtime_mock,
            send_signal=mock.AsyncMock()
        )
        await authenticator._create_community_feed_if_necessary()
        yield authenticator._community_feed
    finally:
        await authenticator.stop()


async def test_start_and_connect(authenticated_feed):
    authenticated_feed.feed_callbacks = {}
    with mock.patch.object(authenticated_feed.authenticator, "is_logged_in", mock.Mock(return_value=True)) \
        as is_logged_in_mock, \
        mock.patch.object(authenticated_feed, "_subscribe_to_table", mock.AsyncMock()) \
        as _subscribe_to_table_mock:
        # without feed_callbacks
        with mock.patch.object(authenticated_feed.authenticator.supabase_client, "get_subscribed_channel_tables",
                               mock.Mock(return_value=[])) as get_subscribed_channel_tables_mock:
            await authenticated_feed.start()
            is_logged_in_mock.assert_not_called()
            _subscribe_to_table_mock.assert_not_called()
            get_subscribed_channel_tables_mock.assert_not_called()
            # with feed_callbacks
            authenticated_feed.feed_callbacks = {"signals": None, "plopplop":None}
            await authenticated_feed.start()
            assert is_logged_in_mock.call_count == 2
            # no sub channel: call _subscribe_to_table
            assert _subscribe_to_table_mock.call_count == 2
            assert get_subscribed_channel_tables_mock.call_count == 2
            get_subscribed_channel_tables_mock.reset_mock()
            is_logged_in_mock.reset_mock()
            _subscribe_to_table_mock.reset_mock()

        with mock.patch.object(authenticated_feed.authenticator.supabase_client, "get_subscribed_channel_tables",
                               mock.Mock(return_value=["signals"])) as get_subscribed_channel_tables_mock:
            # sub channel on signals: call _subscribe_to_table just for plopplop
            await authenticated_feed.start()
            is_logged_in_mock.assert_called_once()
            # no sub channel: call _subscribe_to_table
            _subscribe_to_table_mock.assert_called_with("plopplop")
            assert get_subscribed_channel_tables_mock.call_count == 2
            get_subscribed_channel_tables_mock.reset_mock()
            is_logged_in_mock.reset_mock()
            _subscribe_to_table_mock.reset_mock()

    authenticated_feed.feed_callbacks = {"signals": None, "plopplop":None}
    with pytest.raises(commons_authentication.AuthenticationRequired):
        with mock.patch.object(authenticated_feed.authenticator.supabase_client, "get_subscribed_channel_tables",
                               mock.Mock(return_value=["plop"])), \
             mock.patch.object(authenticated_feed.authenticator, "is_logged_in", mock.Mock(return_value=False)):
                await authenticated_feed.start()

async def test_connection(authenticated_feed):
    with mock.patch.object(authenticated_feed.authenticator, "is_logged_in", mock.Mock(return_value=True)) \
         as is_logged_in_mock:
        with mock.patch.object(authenticated_feed.authenticator.supabase_client, "is_realtime_connected",
                               mock.Mock(return_value=True)) as is_realtime_connected_mock:
            assert authenticated_feed.is_connected_to_remote_feed() is True
            is_realtime_connected_mock.assert_called_once()
            assert authenticated_feed.is_connected() is True
            is_logged_in_mock.assert_called_once()
    with mock.patch.object(authenticated_feed.authenticator, "is_logged_in", mock.Mock(return_value=False)) \
        as is_logged_in_mock:
        with mock.patch.object(authenticated_feed.authenticator.supabase_client, "is_realtime_connected",
                               mock.Mock(return_value=False)) as is_realtime_connected_mock:
            assert authenticated_feed.is_connected_to_remote_feed() is False
            is_realtime_connected_mock.assert_called_once()
            assert authenticated_feed.is_connected() is False
            is_logged_in_mock.assert_called_once()


async def test_subscribe_to_table(authenticated_feed):
    channel_mock = await authenticated_feed._realtime_client.channel()
    authenticated_feed._realtime_client.channel.reset_mock()
    channel_mock.on.assert_not_called()
    channel_mock.subscribe.assert_not_called()

    await authenticated_feed._subscribe_to_table("plop_table")
    authenticated_feed._realtime_client.channel.assert_called_once_with(
        authenticated_feed.SCHEMA, "plop_table"
    )
    channel_mock.on.assert_called_once_with(
        authenticated_feed.INSERT_EVENT, authenticated_feed._message_callback
    )
    channel_mock.subscribe.assert_called_once_with(
        authenticated_feed._subscribed_callback
    )


async def test_register_feed_callback(authenticated_feed):
    assert authenticated_feed.is_signal_receiver is False
    assert authenticated_feed.feed_callbacks == {}
    target_table = authenticated_feed._get_table(commons_enums.CommunityChannelTypes.SIGNAL)

    with mock.patch.object(authenticated_feed, "_subscribe_to_table_if_necessary", mock.AsyncMock()) \
        as _subscribe_to_table_if_necessary_mock:
        await authenticated_feed.register_feed_callback(
            commons_enums.CommunityChannelTypes.SIGNAL, "plop_cb", "identifier"
        )
        assert authenticated_feed.is_signal_receiver is True
        assert authenticated_feed.feed_callbacks == {
            target_table: {
                "identifier": ["plop_cb"]
            }
        }
        _subscribe_to_table_if_necessary_mock.assert_called_once_with(target_table)
        _subscribe_to_table_if_necessary_mock.reset_mock()

        await authenticated_feed.register_feed_callback(
            commons_enums.CommunityChannelTypes.SIGNAL, "plop_cb", "identifier"
        )
        assert authenticated_feed.feed_callbacks == {
            target_table: {
                "identifier": ["plop_cb", "plop_cb"]    # added callback
            }
        }
        _subscribe_to_table_if_necessary_mock.assert_called_once_with(target_table)
        _subscribe_to_table_if_necessary_mock.reset_mock()

        await authenticated_feed.register_feed_callback(
            commons_enums.CommunityChannelTypes.SIGNAL, "plop_cb2"
        )
        assert authenticated_feed.feed_callbacks == {
            target_table: {
                "identifier": ["plop_cb", "plop_cb"],
                None: ["plop_cb2"]
            }
        }
        _subscribe_to_table_if_necessary_mock.assert_called_once_with(target_table)
        _subscribe_to_table_if_necessary_mock.reset_mock()

        # wrong table
        with pytest.raises(NotImplementedError):
            await authenticated_feed.register_feed_callback(
                "wrong type", "plop_cb3"
            )
        assert authenticated_feed.feed_callbacks == {
            target_table: {
                "identifier": ["plop_cb", "plop_cb"],
                None: ["plop_cb2"]
            }
        }
        _subscribe_to_table_if_necessary_mock.assert_not_called()


async def test_send(authenticated_feed):
    assert authenticated_feed.is_signal_receiver is False
    assert authenticated_feed.is_signal_emitter is False
    message = {"text": "ploppp"}
    channel_type = commons_enums.CommunityChannelTypes.SIGNAL
    identifier = "plop_identifier"

    with mock.patch.object(authenticated_feed.authenticator, "is_logged_in", mock.Mock(return_value=False)) \
        as is_logged_in_mock:
        await authenticated_feed.send(message, channel_type, identifier)
        is_logged_in_mock.assert_called_once()

    with mock.patch.object(authenticated_feed.authenticator, "is_logged_in", mock.Mock(return_value=True)) \
        as is_logged_in_mock, \
            mock.patch.object(uuid, "uuid4", mock.Mock(return_value="1")) as uuid4_mock:
        await authenticated_feed.send(message, channel_type, identifier)
        is_logged_in_mock.assert_called_once()
        authenticated_feed.authenticator.supabase_client.send_signal.assert_called_once_with(
            authenticated_feed.SIGNALS_TABLE,
            identifier,
            authenticated_feed._build_message(channel_type, message)
        )
        assert uuid4_mock.call_count == 2   # 2 calls to _build_message


async def test_message_callback(authenticated_feed):
    message = {"text": "ploppp"}
    channel_type = commons_enums.CommunityChannelTypes.SIGNAL
    identifier = "plop_identifier"
    message_dict = {
        "table": authenticated_feed._get_table(channel_type),
        "new": {
            "signal": json.loads(authenticated_feed._build_message(channel_type, message)),
            supabase_enums.SignalKeys.PRODUCT_ID.value: identifier
        },
    }
    # no callback
    await authenticated_feed._message_callback(message_dict)
    callback = mock.AsyncMock()
    with mock.patch.object(authenticated_feed, "_subscribe_to_table_if_necessary", mock.AsyncMock()) \
        as _subscribe_to_table_if_necessary_mock:
        await authenticated_feed.register_feed_callback(channel_type, callback, identifier=identifier)
        _subscribe_to_table_if_necessary_mock.assert_called_once()

    # new message for new message_id
    json_message = json.loads(authenticated_feed._build_message(channel_type, message))
    message_dict["new"]["signal"] = json_message
    await authenticated_feed._message_callback(message_dict)
    callback.assert_called_once_with(json_message)
    callback.reset_mock()
    # same message, ignored
    await authenticated_feed._message_callback(message_dict)
    callback.assert_not_called()

    # register other callbacks
    callback_2 = mock.AsyncMock()
    callback_3 = mock.AsyncMock()
    callback_4 = mock.AsyncMock()
    with mock.patch.object(authenticated_feed, "_subscribe_to_table_if_necessary", mock.AsyncMock()) \
        as _subscribe_to_table_if_necessary_mock:
        await authenticated_feed.register_feed_callback(channel_type, callback_2, identifier=identifier)
        await authenticated_feed.register_feed_callback(channel_type, callback_3, identifier="other")
        await authenticated_feed.register_feed_callback(channel_type, callback_4)
        assert _subscribe_to_table_if_necessary_mock.call_count == 3

    # new message for new message_id
    json_message = json.loads(authenticated_feed._build_message(channel_type, message))
    message_dict["new"]["signal"] = json_message
    await authenticated_feed._message_callback(message_dict)
    callback.assert_called_once_with(json_message)
    callback_2.assert_called_once_with(json_message)
    callback_3.assert_not_called()    # different identifier
    callback_4.assert_not_called()    # different identifier
