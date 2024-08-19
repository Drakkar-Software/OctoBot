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
import copy
import typing
import gotrue.errors
import postgrest
import supabase


class AuthenticatedAsyncSupabaseClient(supabase.AClient):
    async def init_other_postgrest_client(
        self, supabase_url: str = None, supabase_key: str = None, schema: str = "public"
    ) -> postgrest.AsyncPostgrestClient:
        supabase_key = supabase_key or self.supabase_key
        options = copy.deepcopy(self.options)
        options.storage = None
        options.schema = schema
        if supabase_key != self.supabase_key:
            auth_headers = self._get_auth_headers(authorization=self._create_auth_header(supabase_key))
            # use local supabase key instead of self.supabase_key that is set by _get_auth_headers
            auth_headers["apiKey"] = supabase_key
            options.headers.update(auth_headers)
        return self._init_postgrest_client(
            rest_url=f"{supabase_url}/rest/v1" if supabase_url else self.rest_url,
            headers=options.headers,
            schema=options.schema,
            timeout=options.postgrest_client_timeout,
        )

    def remove_session_details(self):
        self.auth._remove_session()
        self.auth._notify_all_subscribers("SIGNED_OUT", None)

    # OVERRIDE TO AVOID WARNING
    def _listen_to_auth_events(
        self, event: gotrue.types.AuthChangeEvent, session: typing.Union[gotrue.types.Session, None]
    ):
        access_token = self.supabase_key
        if event in ["SIGNED_IN", "TOKEN_REFRESHED", "SIGNED_OUT"]:
            # reset postgrest and storage instance on event change
            self._postgrest = None
            self._storage = None
            self._functions = None
            access_token = session.access_token if session else self.supabase_key

        self.options.headers["Authorization"] = self._create_auth_header(access_token)

        # REMOVED TO AVOID WARNING
        # # set_auth is a coroutine, how to handle this?
        # self.realtime.set_auth(access_token)

    async def aclose(self):
        # waiting from supabase close() method
        try:
            await self.auth.close()
        except RuntimeError:
            # can happen when "Event loop is closed"
            pass
        if self.realtime.is_connected:
            await self.realtime.close()
        if self._postgrest:
            try:
                await self._postgrest.aclose()
            except RuntimeError:
                # can happen when "Event loop is closed"
                pass
        if self._storage:
            await self._storage.aclose()
        # timer has to be stopped, there is no public stop api
        if self.auth._refresh_token_timer:
            self.auth._refresh_token_timer.cancel()
            self.auth._refresh_token_timer = None