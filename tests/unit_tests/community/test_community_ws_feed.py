#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
import asyncio
import json
import time
import websockets

import octobot.community as community
import octobot.constants as constants
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.enums as commons_enums
import octobot_commons.signals as commons_signals

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

HOST = "127.0.0.1"
PORT = 8765
TOKEN = "acb1"

DATA_DICT = {
    "data": "yes",
    "content": {
        "hi": 1,
        "a": [
            "@@@",
            1
        ]
    }
}


class MockedResponse:
    def __init__(self, status_code=200, json=None):
        self.status_code = status_code
        self.json_resp = json

    def json(self):
        return self.json_resp


def _mocked_signal():
    return commons_signals.Signal(
        "identifier", 
        {
            "key1": 11,
            "key2": "random value"
        }
    )


def _build_message(value):
    return {
        commons_enums.CommunityFeedAttrs.VERSION.value: constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION,
        commons_enums.CommunityFeedAttrs.CHANNEL_TYPE.value: commons_enums.CommunityChannelTypes.SIGNAL.value,
        commons_enums.CommunityFeedAttrs.STREAM_ID.value: 1,
        commons_enums.CommunityFeedAttrs.VALUE.value: value
    }


async def echo_or_signal_reply_handler(websocket, _):
    async for message in websocket:
        parsed_message = json.loads(message)
        if parsed_message.get("command") == "subscribe":
            await websocket.send(json.dumps({"type": "confirm_subscription"}))
        else:
            value = json.loads(json.loads(parsed_message.get("data", "")).get("value"))
            base_message = _build_message(_mocked_signal().to_dict() if value == "signal" else value)
            await websocket.send(json.dumps({"message": base_message}))


@pytest_asyncio.fixture
async def community_echo_server():
    async with websockets.serve(echo_or_signal_reply_handler, HOST, PORT):
        yield


@pytest_asyncio.fixture
async def authenticator():
    community.IdentifiersProvider.use_production()
    auth = community.CommunityAuthentication(None, None)
    auth._auth_token = TOKEN
    auth.refresh_token = TOKEN
    auth._expire_at = 11
    return auth


@pytest_asyncio.fixture
async def community_mocked_consumer_server():
    mock_consumer = mock.AsyncMock()

    async def mock_handler(websocket, path):
        async for message in websocket:
            await mock_consumer(message)
            parsed_message = json.loads(message)
            if parsed_message.get("command") == "subscribe":
                await websocket.send(json.dumps({"type": "confirm_subscription"}))
            else:
                await websocket.send(json.dumps({"message": _build_message(mock_consumer.call_count)}))
    async with websockets.serve(mock_handler, HOST, PORT):
        yield mock_consumer


@pytest_asyncio.fixture
async def connected_community_feed(authenticator):
    feed = None
    try:
        feed = community.CommunityWSFeed(f"ws://{HOST}:{PORT}", authenticator)
        feed.INIT_TIMEOUT = 1
        with mock.patch.object(feed, "_fetch_stream_identifier", mock.AsyncMock(return_value=1)) \
                as _fetch_stream_identifier_mock:
            await feed.register_feed_callback(commons_enums.CommunityChannelTypes.SIGNAL, mock.AsyncMock())
            _fetch_stream_identifier_mock.assert_called_once_with(None)
            await feed.start()
            yield feed
    finally:
        if feed is not None:
            await feed.stop()


async def test_consume_base_message(community_echo_server, connected_community_feed):
    consume_mock = connected_community_feed.feed_callbacks[commons_enums.CommunityChannelTypes.SIGNAL][None][0]
    consume_mock.assert_not_called()
    await connected_community_feed.send("hiiiii", commons_enums.CommunityChannelTypes.SIGNAL, None)
    await _wait_for_receive()
    consume_mock.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': 'hiiiii'})
    consume_mock.reset_mock()

    await connected_community_feed.send(json.dumps(DATA_DICT), commons_enums.CommunityChannelTypes.SIGNAL, None)
    await _wait_for_receive()
    consume_mock.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': json.dumps(DATA_DICT)})


async def test_consume_signal_message(community_echo_server, connected_community_feed):
    # use strat1 as identifier
    consume_mock = connected_community_feed.feed_callbacks[commons_enums.CommunityChannelTypes.SIGNAL][None][0]
    connected_community_feed.feed_callbacks = {
        commons_enums.CommunityChannelTypes.SIGNAL: {
            "strat1": [consume_mock]
        }
    }
    connected_community_feed._identifier_by_stream_id[1] = "strat1"
    consume_mock.assert_not_called()
    await connected_community_feed.send("signal", commons_enums.CommunityChannelTypes.SIGNAL, "strat1")
    await _wait_for_receive()
    consume_mock.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': _mocked_signal().to_dict()})


async def test_send_base_message(community_mocked_consumer_server, connected_community_feed):
    community_mocked_consumer_server.assert_called_once_with(
        '{"command": "subscribe", "identifier": "{\\"channel\\": \\"Spree::MessageChannel\\"}", "data": {}}'
    )
    community_mocked_consumer_server.reset_mock()
    consume_mock = connected_community_feed.feed_callbacks[commons_enums.CommunityChannelTypes.SIGNAL][None][0]
    consume_mock.assert_not_called()
    await connected_community_feed.send("signal", commons_enums.CommunityChannelTypes.SIGNAL, None)
    await _wait_for_receive()
    community_mocked_consumer_server.assert_called_once_with(
        '{"command": "message", "identifier": "{\\"channel\\": \\"Spree::MessageChannel\\"}", "data": '
        '"{\\"topic\\": \\"t\\", \\"feed_id\\": 1, \\"version\\": \\"1.0.0\\", '
        '\\"value\\": \\"\\\\\\"signal\\\\\\"\\"}"}'
    )
    consume_mock.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': 1})
    consume_mock.reset_mock()

    await connected_community_feed.send(DATA_DICT, commons_enums.CommunityChannelTypes.SIGNAL, None)
    await _wait_for_receive()
    assert community_mocked_consumer_server.call_count == 2
    identifier_str = json.dumps({"channel": "Spree::MessageChannel"})
    sub_data_str = json.dumps({"data": "yes", "content": {"hi": 1, "a": ["@@@", 1]}})
    data_str = json.dumps({"topic": "t", "feed_id": 1, "version": "1.0.0", "value": sub_data_str})
    assert community_mocked_consumer_server.mock_calls[1].args == \
       (json.dumps({"command": "message", "identifier": identifier_str, "data": data_str}), )
    consume_mock.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': 2})


async def test_send_signal_message(community_mocked_consumer_server, connected_community_feed):
    community_mocked_consumer_server.assert_called_once_with(
        '{"command": "subscribe", "identifier": "{\\"channel\\": \\"Spree::MessageChannel\\"}", "data": {}}'
    )
    community_mocked_consumer_server.reset_mock()
    consume_mock = connected_community_feed.feed_callbacks[commons_enums.CommunityChannelTypes.SIGNAL][None][0]
    consume_mock.assert_not_called()
    await connected_community_feed.send(_mocked_signal().to_dict(),
                                        commons_enums.CommunityChannelTypes.SIGNAL, None)
    await _wait_for_receive()

    identifier_str = json.dumps({"channel": "Spree::MessageChannel"})
    sub_data_str = json.dumps(_mocked_signal().to_dict())
    data_str = json.dumps({"topic": "t", "feed_id": 1, "version": "1.0.0", "value": sub_data_str})
    community_mocked_consumer_server.assert_called_once_with(
        json.dumps({"command": "message", "identifier": identifier_str, "data": data_str}))
    consume_mock.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': 1})


async def test_reconnect(authenticator):
    server = client = None
    try:
        server = await websockets.serve(echo_or_signal_reply_handler, HOST, PORT)
        client_handler = mock.AsyncMock()
        client = community.CommunityWSFeed(f"ws://{HOST}:{PORT}", authenticator)
        client.RECONNECT_DELAY = 0
        await client.register_feed_callback(commons_enums.CommunityChannelTypes.SIGNAL, client_handler)
        await client.start()

        # 1. ensure client is both receiving and sending messages
        client_handler.assert_not_called()
        await client.send("plop", commons_enums.CommunityChannelTypes.SIGNAL, None)
        await _wait_for_receive()
        client_handler.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': "plop"})
        client_handler.reset_mock()
        await client.send("hii", commons_enums.CommunityChannelTypes.SIGNAL, None)
        await _wait_for_receive()
        client_handler.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': "hii"})
        client_handler.reset_mock()

        # 2. client is disconnected (server closes)
        server.close()
        await server.wait_closed()
        with pytest.raises(websockets.ConnectionClosed):
            await client.send("hii", commons_enums.CommunityChannelTypes.SIGNAL, None,
                              reconnect_if_necessary=False)
        await _wait_for_receive()
        client_handler.assert_not_called()

        # 3. client is reconnected (server restarts)
        server = await websockets.serve(echo_or_signal_reply_handler, HOST, PORT)
        # ensure the previous message was not get sent upon reconnection
        client_handler.assert_not_called()

        # 4. re-exchange message using the same client (reconnected through send method)
        assert not client.is_connected()
        await client.send("plop", commons_enums.CommunityChannelTypes.SIGNAL, None)
        await _wait_for_connection_and_subscribe(client)
        await _wait_for_receive()
        client_handler.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': "plop"})
        client_handler.reset_mock()
        await client.send("hii", commons_enums.CommunityChannelTypes.SIGNAL, None)
        await _wait_for_receive()
        client_handler.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': "hii"})
        client_handler.reset_mock()

        # 5. re disconnect server
        server.close()
        await server.wait_closed()
        with pytest.raises(websockets.ConnectionClosed):
            await client.send("hii", commons_enums.CommunityChannelTypes.SIGNAL, None,
                              reconnect_if_necessary=False)
        await _wait_for_receive()
        client_handler.assert_not_called()

        # 6. wait for client reconnection, receive signal as soon as possible
        server = await websockets.serve(echo_or_signal_reply_handler, HOST, PORT)
        client_handler.assert_not_called()
        # wait for client reconnection
        await _wait_for_connection_and_subscribe(client)

        # 7. send message from server with a consuming only client
        await next(iter(server.websockets)).send(json.dumps({"message": _build_message("greetings")}))
        await _wait_for_receive()
        assert client.is_connected()
        # client_handler is called as the consume task did reconnect the client
        client_handler.assert_called_once_with({'v': '1.0.0', 't': 't', 'i': 1, 's': "greetings"})

    finally:
        if client is not None:
            await client.stop()
        if server is not None:
            server.close()
            await server.wait_closed()


async def _wait_for_connection_and_subscribe(client):
    t0 = time.time()
    while time.time() - t0 < 5:
        if client.is_connected() and client.is_subscribed:
            break
        else:
            await asyncio.sleep(0.05)
    assert client.is_connected()
    assert client.is_subscribed


async def _wait_for_receive(wait_cycles=8):
    # 5 necessary wait_cycles for both sending, receiving, replying and receiving a reply
    for _ in range(wait_cycles):
        # wait for websockets lib trigger client
        await asyncio_tools.wait_asyncio_next_cycle()
