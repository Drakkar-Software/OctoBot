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
import asyncio
import json
import urllib.parse
import websockets
import realtime
import logging

import octobot_commons.logging as commons_logging
import octobot.community.supabase_backend.supabase_realtime_channel as supabase_realtime_channel


# disable websockets logger
logging.getLogger("websockets.client").setLevel(logging.WARNING)


class AuthenticatedSupabaseRealtimeSocket(realtime.Socket):
    def __init__(self, url: str, auto_reconnect: bool = False, params: dict = {}, hb_interval: int = 5):
        """
        from realtime.Socket docs:
        `Socket` is the abstraction for an actual socket connection that receives and 'reroutes' `Message` according to its `topic` and `event`.
        Socket-Channel has a 1-many relationship.
        Socket-Topic has a 1-many relationship.
        :param url: Websocket URL of the Realtime server. starts with `ws://` or `wss://`
        :param params: Optional parameters for connection.
        :param hb_interval: WS connection is kept alive by sending a heartbeat message. Optional, defaults to 5.
        """
        # local override of super().__init__() to avoid python 3.8 incompatibility
        self.url = url
        self.channels = {}
        self.connected = False
        self.params = params
        self.hb_interval = hb_interval
        self.kept_alive = False
        self.auto_reconnect = auto_reconnect

        self.logger = commons_logging.get_logger(self.__class__.__name__)
        self.closed = True
        self.pending_subscribe_callbacks = {}
        self.system_callbacks = {}
        self.listen_task = None
        self.ws_connection = None

    def set_channel(self, schema: str, table_name: str) -> supabase_realtime_channel.AuthenticatedSupabaseRealtimeChannel:
        topic = (
            f"realtime:{schema}"
            if table_name == "*"
            else f"realtime:{schema}:{table_name}"
        )
        chan = supabase_realtime_channel.AuthenticatedSupabaseRealtimeChannel(
            self, topic, schema, table_name, self.params
        )
        try:
            self.channels[topic].append(chan)
        except KeyError:
            self.channels[topic] = [chan]
        return chan

    def register_subscribe_callback(self, topic, callback):
        if topic not in self.pending_subscribe_callbacks:
            self.pending_subscribe_callbacks[topic] = [callback]
        else:
            self.pending_subscribe_callbacks[topic].append(callback)

    def register_system_callback(self, topic, callback):
        if topic not in self.system_callbacks:
            self.system_callbacks[topic] = [callback]
        else:
            self.system_callbacks[topic].append(callback)

    async def _listen(self) -> None:
        """
        local override to handle errors and async callbacks and methods
        from realtime.Socket docs:
        An infinite loop that keeps listening.
        :return: None
        """
        try:
            reconnect_delay = 0
            while True:
                try:
                    msg = await self.ws_connection.recv()
                    # success as a message is received: reset reconnect delay
                    reconnect_delay = 0
                    await self._on_message(msg)
                except websockets.ConnectionClosed as err:  # pylint: disable=no-member
                    if self.closed or not self.auto_reconnect:
                        # should not try to reconnect, exit loop iteration
                        self.logger.exception(err, True, f"Realtime connection closed.")
                        break
                    # not closed and should reconnect: try to reconnect
                    self.logger.info("The realtime connection with server closed, trying to reconnect...")
                    if not await self.aconnect():
                        # reconnect failed, retry in next loop (ConnectionClosed will be raised again)
                        # exponential reconnect delay, caped at 60 seconds
                        reconnect_delay = min((reconnect_delay + 1) * 2, 60)
                        self.logger.info(f"Realtime reconnect failed. Next attempt in {reconnect_delay} seconds.")
                        await asyncio.sleep(reconnect_delay)
                        continue
                    # reconnect success: resubscribe and listen again in next loop iteration
                    await self.subscribe_channels()
        except Exception as err:
            self.logger.exception(err, True, f"Unexpected error when listening to  realtime message: {err}")
            raise

    async def subscribe_channels(self):
        for channels in self.channels.values():
            for channel in channels:
                if not (channel.is_joined() or channel.is_joining()):
                    await channel.subscribe()

    def _set_closed_channel_states(self):
        for channels in self.channels.values():
            for channel in channels:
                channel.state = supabase_realtime_channel.CHANNEL_STATES.CLOSED

    async def _on_message(self, text_msg):
        try:
            msg = realtime.Message(**json.loads(text_msg))

            if msg.event == realtime.ChannelEvents.reply:
                for subscribe_cb in self.pending_subscribe_callbacks.get(msg.topic, []):
                    await subscribe_cb(self.get_subscribe_result(msg), msg)
                # skip next callbacks
                return

            if msg.event == 'system':
                for system_cb in self.system_callbacks.get(msg.topic, []):
                    await system_cb(msg)
                # skip next callbacks
                return

            for channel in self.channels.get(msg.topic, []):
                for cl in channel.listeners:
                    if cl.event in ["*", msg.event]:
                        await cl.callback(msg.payload)
        except Exception as err:
            self.logger.exception(err, True, f"Error when processing realtime message: {err}")
            raise

    def get_subscribe_result(self, message: realtime.Message):
        # inspired from https://github.com/supabase/realtime-js/blob/master/src/RealtimeChannel.ts#L220
        if message.payload.get("status", None) == "ok":
            return "SUBSCRIBED"
        if message.payload.get("status", None) == "error":
            return "CHANNEL_ERROR"
        if message.payload.get("status", None) == "timeout":
            return "TIMED_OUT"

    async def alisten(self):
        try:
            await asyncio.gather(self._listen(), self._keep_alive())
        except Exception as err:
            self.logger.exception(err, True, f"Unexpected exception in listen loop: {err}")

    async def aconnect(self):
        try:
            await self._close_ws_connection_if_any()
            self.closed = False
            ws_connection = await websockets.connect(f"{self.url}?{urllib.parse.urlencode(self.params)}")  # pylint: disable=no-member
            if self.closed:
                # was closed while connecting, don't keep this connection
                await ws_connection.close()
                return
            if ws_connection.open:
                self.logger.info("Realtime socket connected")
                self.ws_connection = ws_connection
                self.connected = True
                if self.listen_task is None or self.listen_task.done():
                    self.listen_task = asyncio.create_task(self.alisten())
                return True
        except (OSError, OSError, asyncio.TimeoutError, websockets.exceptions.InvalidHandshake) as err:
            self.logger.exception(err, True, f"Error when connecting to realtime websocket: {err}")
        except Exception as err:
            self.logger.exception(err, True, f"Unexpected error when connecting to realtime websocket: {err}")
        return False

    async def close(self):
        if not self.closed:
            self.logger.debug("closing realtime connection")
        self.closed = True
        if self.listen_task and not self.listen_task.done():
            self.listen_task.cancel()
        self.connected = False
        await self._close_ws_connection_if_any()

    async def _close_ws_connection_if_any(self):
        if self.ws_connection is not None:
            self._set_closed_channel_states()
            await self.ws_connection.close()
