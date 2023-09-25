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

import octobot.community.supabase_backend.supabase_realtime_socket as supabase_realtime_socket
import octobot.community.supabase_backend.supabase_realtime_channel as supabase_realtime_channel


class AuthenticatedSupabaseRealtimeClient:
    """
    Full rewrite of https://github.com/supabase-community/supabase-py/blob/develop/supabase/lib/realtime_client.py
    as it can't be used as is and is too far from the js implementation.

    AuthenticatedSupabaseRealtimeClient tries to expose a similar logic and public API
    as https://github.com/supabase/realtime-js/blob/master/src/RealtimeClient.ts
    """
    AUTH_TIMEOUT = 60

    def __init__(self, realtime_url: str, supabase_key: str):
        self.supabase_key = supabase_key
        self.socket = supabase_realtime_socket.AuthenticatedSupabaseRealtimeSocket(
            realtime_url,
            auto_reconnect=True,
            params={"apikey": supabase_key}
        )
        self.channels = []
        self.access_token = None
        self.update_auth_tasks = []

    async def channel(self, schema: str, table_name: str) \
            -> supabase_realtime_channel.AuthenticatedSupabaseRealtimeChannel:
        await self._ensure_connection()
        chan = self.socket.set_channel(schema, table_name)
        chan.update_auth_payload(self._get_auth_payload_update())
        self.channels.append(chan)
        return chan

    def set_auth(self, access_token, loop=None):
        # similar to https://github.com/supabase/realtime-js/blob/master/src/RealtimeClient.ts#L273
        self.access_token = access_token
        loop = loop or asyncio.get_running_loop()
        if access_token is None:
            # access_token is None: no user is signed in
            if not self.socket.closed:
                # close open realtime clients when user signs out
                self.update_auth_tasks.append(
                    loop.create_task(self.close())
                )
            return
        # access_token is not None: use is authenticated
        channel_auth_update_coros = []
        for channels in self.socket.channels.values():
            for channel in channels:
                channel.update_auth_payload(self._get_auth_payload_update())
                # channel already connected (joined), auth into channel if necessary
                if channel.joined_once and channel.is_joined():
                    channel_auth_update_coros.append(channel.auth())
        # user is signed in: can update channel auth
        self.update_auth_tasks.append(
            loop.create_task(self._on_successful_auth(self.socket.closed, channel_auth_update_coros))
        )

    async def close(self):
        await self.socket.close()
        self.update_auth_tasks.clear()

    async def _on_successful_auth(self, should_reopen, coros):
        if should_reopen and self.socket.channels:
            # connection might have been closed in a previous sign-out
            await self._ensure_connection()
        if coros:
            await asyncio.gather(*coros)

    def _get_auth_payload_update(self):
        return {'access_token': self.access_token}

    async def _ensure_connection(self):
        if (not self.socket.connected) or self.socket.closed:
            await self.socket.aconnect()
            await self.socket.subscribe_channels()
