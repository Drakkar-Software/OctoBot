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
import random
import time

import websockets
import asyncio
import enum
import json
import packaging.version as packaging_version

import octobot_commons.errors as commons_errors
import octobot_commons.enums as commons_enums
import octobot_commons.authentication as authentication
import octobot.constants as constants
import octobot.community.feeds.abstract_feed as abstract_feed
import octobot.community.identifiers_provider as identifiers_provider


class COMMANDS(enum.Enum):
    SUBSCRIBE = "subscribe"
    MESSAGE = "message"


class CHANNELS(enum.Enum):
    MESSAGE = "Spree::MessageChannel"


class CommunityWSFeed(abstract_feed.AbstractFeed):
    INIT_TIMEOUT = 60
    RECONNECT_DELAY = 15
    STALE_CONNECTION_TIMEOUT = 30   # ws server sends a ping every 3s

    def __init__(self, feed_url, authenticator):
        super().__init__(feed_url, authenticator)
        self.websocket_connection = None
        self.lock = asyncio.Lock()

        self.consumer_task = None
        self.watcher_task = None
        self._identifier_by_stream_id = {}
        self._reconnect_attempts = 0
        self._last_ping_time = None

    async def start(self):
        await self._ensure_connection()
        if self.consumer_task is None or self.consumer_task.done():
            self.consumer_task = asyncio.create_task(self.start_consumer())
        if self.watcher_task is None or self.watcher_task.done():
            self.watcher_task = asyncio.create_task(self.connection_watcher())

    async def stop(self):
        self.logger.debug("Stopping ...")
        self.should_stop = True
        if self.websocket_connection is not None:
            await self.websocket_connection.close()
        if self.consumer_task is not None:
            self.consumer_task.cancel()
        if self.watcher_task is not None:
            self.watcher_task.cancel()
        self.logger.debug("Stopped")

    # pylint: disable=E1101
    async def start_consumer(self):
        while not self.should_stop:
            try:
                await self._ensure_connection()
                async for message in self.websocket_connection:
                    try:
                        await self.consume(message)
                    except Exception as e:
                        self.logger.exception(e, True, f"Error while consuming feed: {e}")
            except (websockets.ConnectionClosedError, ConnectionRefusedError):
                if self._reconnect_attempts == 0:
                    self.logger.warning(f"Disconnected from community, reconnecting now.")
                    # first reconnect instantly
                else:
                    # use self.RECONNECT_DELAY + or - 0-10 %
                    reconnect_delay = self.RECONNECT_DELAY * (1 + (random.random() * 2 - 1) / 10)
                    self.logger.warning(f"Disconnected from community, retrying to connect in {reconnect_delay}s "
                                        f"({self._reconnect_attempts} attempts)")
                    if reconnect_delay > 0:
                        await asyncio.sleep(reconnect_delay)
            except Exception as e:
                self.logger.exception(e, True, f"Unexpected exception when receiving community feed: {e}")

    async def connection_watcher(self):
        while not self.should_stop:
            await asyncio.sleep(self.STALE_CONNECTION_TIMEOUT)
            if self._last_ping_time is not None and \
                    time.time() - self._last_ping_time > self.STALE_CONNECTION_TIMEOUT:
                self.logger.error("Stale community connection detected, resetting the connection")
                # close websocket_connection, the next _ensure_connection call will restart it
                await self.websocket_connection.close()

    async def consume(self, message):
        if message.startswith('{"type":"ping"'):
            self._last_ping_time = time.time()
            return
        parsed_message = json.loads(message)["message"]
        try:
            self._ensure_supported(parsed_message)
            for callback in self._get_callbacks(parsed_message):
                await callback(parsed_message)
        except commons_errors.UnsupportedError as e:
            self.logger.error(f"Unsupported message: {e}")

    def _ensure_supported(self, parsed_message):
        if packaging_version.Version(parsed_message[commons_enums.CommunityFeedAttrs.VERSION.value]) \
                < packaging_version.Version(constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION):
            raise commons_errors.UnsupportedError(
                f"Minimum version: {constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION}"
            )

    async def send(self, message, channel_type, identifier,
                   command=COMMANDS.MESSAGE.value, reconnect_if_necessary=True):
        if reconnect_if_necessary:
            await self._ensure_connection()
        if identifier is not None:
            await self._ensure_stream_identifier(identifier)
        await self.websocket_connection.send(self._build_ws_message(message, channel_type, command, identifier))

    def _build_ws_message(self, message, channel_type, command, identifier):
        return json.dumps({
            "command": command,
            "identifier": self._build_channel_identifier(),
            "data": self._build_data(channel_type, identifier, message)
        })

    def _build_data(self, channel_type, identifier, message):
        if message:
            return json.dumps({
                "topic": channel_type.value,
                "feed_id": self._build_stream_id(identifier),
                "version": constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION,
                "value": json.dumps(message),
            })
        return {}

    async def register_feed_callback(self, channel_type, callback, identifier=None):
        """
        Registers a feed callback
        """
        await self._ensure_stream_identifier(identifier)
        if identifier not in list(self._identifier_by_stream_id.values()):
            stream_id = await self._fetch_stream_identifier(identifier)
            self._identifier_by_stream_id[stream_id] = identifier
        try:
            self.feed_callbacks[channel_type][identifier].append(callback)
        except KeyError:
            if channel_type not in self.feed_callbacks:
                self.feed_callbacks[channel_type] = {}
            self.feed_callbacks[channel_type][identifier] = [callback]

    async def _ensure_stream_identifier(self, identifier):
        if identifier not in list(self._identifier_by_stream_id.values()):
            stream_id = await self._fetch_stream_identifier(identifier)
            self._identifier_by_stream_id[stream_id] = identifier

    async def _fetch_stream_identifier(self, identifier):
        if identifier is None:
            return None
        async with self.authenticator.get_aiohttp_session().get(
                f"{identifiers_provider.IdentifiersProvider.COMMUNITY_URL}api/v2/storefront/feeds/id/{identifier}"
        ) as resp:
            return (await resp.json())["feed_id"]

    def _get_callbacks(self, parsed_message):
        channel_type = self._get_channel_type(parsed_message)
        for callback in self.feed_callbacks.get(channel_type, {}).get(None, ()):
            yield callback
        try:
            identifier = self._get_identifier(parsed_message)
        except KeyError:
            self.logger.debug(f"Unknown feed identifier: "
                              f"{parsed_message[commons_enums.CommunityFeedAttrs.STREAM_ID.value]}")
            return
        if identifier is None:
            # do not yield the same callback twice
            return
        for callback in self.feed_callbacks.get(channel_type, {}).get(identifier, ()):
            yield callback

    def _get_channel_type(self, message):
        return commons_enums.CommunityChannelTypes(message[commons_enums.CommunityFeedAttrs.CHANNEL_TYPE.value])

    def _get_identifier(self, message):
        return self._identifier_by_stream_id[message[commons_enums.CommunityFeedAttrs.STREAM_ID.value]]

    def _build_channel_identifier(self):
        return json.dumps({
            "channel": CHANNELS.MESSAGE.value
        })

    def _build_stream_id(self, requested_identifier):
        for stream_id, identifier in self._identifier_by_stream_id.items():
            if requested_identifier == identifier:
                return stream_id
        return None

    async def _subscribe(self):
        await self.send({}, None, None, command=COMMANDS.SUBSCRIBE.value)
        # waiting for subscription confirmation
        try:
            await asyncio.wait_for(self._get_subscribe_answer(), self.INIT_TIMEOUT)
        except asyncio.TimeoutError:
            raise authentication.AuthenticationError(f"Failed to subscribe to feed")

    async def _get_subscribe_answer(self):
        async for message in self.websocket_connection:
            self.logger.debug("Waiting for subscription confirmation...")
            resp = json.loads(message)
            # TODO handle subscribe errors
            if resp.get("type") and resp.get("type") == "confirm_subscription":
                self.subscribed = True
                return

    # pylint: disable=E1101
    async def _ensure_connection(self):
        if not self.is_connected():
            async with self.lock:
                if not self.is_connected():
                    # (re)connect websocket
                    self._reconnect_attempts += 1
                    await self._connect()
                    self._reconnect_attempts = 0

    async def _connect(self):
        self.subscribed = False
        if self.authenticator.initialized_event is not None:
            await asyncio.wait_for(self.authenticator.initialized_event.wait(), self.INIT_TIMEOUT)
        if not self.authenticator.is_logged_in():
            raise authentication.AuthenticationRequired("OctoBot Community authentication is required to "
                                                        "use community trading signals")
        self.websocket_connection = await websockets.connect(self.feed_url,
                                                             extra_headers=self.authenticator.get_backend_headers(),
                                                             ping_interval=None)
        await self._subscribe()
        self.logger.info("Connected to community feed")

    def is_connected(self):
        return self.websocket_connection is not None and self.websocket_connection.open
