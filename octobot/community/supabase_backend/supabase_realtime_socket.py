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
import websockets
import websockets.exceptions
import realtime

import octobot_commons.logging as logging
import octobot_commons.authentication as authentication
import octobot.community.supabase_backend.supabase_realtime_channel as supabase_realtime_channel


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
        super().__init__(url, auto_reconnect=auto_reconnect, params=params, hb_interval=hb_interval)
        self.logger = logging.get_logger(self.__class__.__name__)
        self.is_closed = False
        self.pending_subscribe_callbacks = {}
        self.listen_task = None

    def set_channel(self, schema: str, table_name: str) -> supabase_realtime_channel.AuthenticatedSupabaseRealtimeChannel:
        topic = (
            f"realtime:{schema}"
            if table_name == "*"
            else f"realtime:{schema}:{table_name}"
        )
        chan = supabase_realtime_channel.AuthenticatedSupabaseRealtimeChannel(
            self, topic, schema, table_name, self.params
        )
        self.channels[topic].append(chan)
        return chan

    def register_subscribe_callback(self, topic, callback):
        if topic not in self.pending_subscribe_callbacks:
            self.pending_subscribe_callbacks[topic] = [callback]
        else:
            self.pending_subscribe_callbacks[topic].append(callback)

    async def _listen(self) -> None:
        """
        local override to handle errors and async callbacks and methods
        from realtime.Socket docs:
        An infinite loop that keeps listening.
        :return: None
        """
        while True:
            try:
                msg = await self.ws_connection.recv()
                msg = realtime.Message(**json.loads(msg))

                if msg.event == realtime.ChannelEvents.reply:
                    for subscribe_cb in self.pending_subscribe_callbacks.get(msg.topic, []):
                        await subscribe_cb(self.get_subscribe_result(msg), msg)
                    continue

                for channel in self.channels.get(msg.topic, []):
                    for cl in channel.listeners:
                        if cl.event in ["*", msg.event]:
                            await cl.callback(msg.payload)
            except websockets.exceptions.ConnectionClosed as err:
                if self.is_closed:
                    break
                if self.auto_reconnect:
                    self.logger.info("The realtime connection with server closed, trying to reconnect...")
                    await self.aconnect()
                    for topic, channels in self.channels.items():
                        for channel in channels:
                            await channel.ajoin()
                else:
                    self.logger.exception(err, True, f"The realtime connection with the server closed. ({err})")
                    break

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
        ws_connection = await websockets.connect(f"{self.url}?apikey={self.params['apikey']}")   #todo improve
        if ws_connection.open:
            self.ws_connection = ws_connection
            self.connected = True
            self.listen_task = asyncio.create_task(self.alisten())
        else:
            raise authentication.AuthenticationError("Realtime connection failed.")

    async def close(self):
        self.is_closed = True
        if self.listen_task and not self.listen_task.done():
            self.listen_task.cancel()
        await self.ws_connection.close()
