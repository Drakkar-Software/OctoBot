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
import copy
import typing
import storage3
import storage3.constants
import gotrue
import gotrue.errors
import postgrest
import supabase.lib.client_options

import octobot.community.supabase_backend.postgres_functions as postgres_functions
import octobot.community.supabase_backend.supabase_realtime_client as supabase_realtime_client


class AuthenticatedAsyncSupabaseClient(supabase.Client):
    """
    supabase.Client subclass to handle:
    - authenticated calls
    - database functions calls
    - auth token refresh
    - realtime client
    There should not be OctoBot specific code here
    """
    REQUEST_TIMEOUT = 30    # default timeout is 5 which is sometimes not enough
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        options: supabase.lib.client_options.ClientOptions = supabase.lib.client_options.ClientOptions(),
        loop=None,
    ):
        self.options = options
        self.options.postgrest_client_timeout = self.REQUEST_TIMEOUT
        self.auth: gotrue.SyncGoTrueClient = None
        self.postgrest: postgrest.AsyncPostgrestClient = None
        super().__init__(supabase_url, supabase_key, options=options)
        self.realtime: supabase_realtime_client.AuthenticatedSupabaseRealtimeClient = self._init_realtime_client(
            self.realtime_url,
            self.supabase_key,
        )
        # update postgres authentication upon auth state change
        self.auth.on_auth_state_change(self._use_auth_session)
        self.event_loop = None

    @staticmethod
    def _init_postgrest_client(
        rest_url: str,
        supabase_key: str,
        headers: typing.Dict[str, str],
        timeout,    # skip typing to avoid httpx import
        schema: str = "public",
    ) -> postgrest.AsyncPostgrestClient:
        """Private helper for creating an instance of the Postgrest client."""
        # Override to use postgrest.AsyncPostgrestClient and allow async requests
        client = postgrest.AsyncPostgrestClient(
            rest_url, headers=headers, schema=schema, timeout=timeout
        )
        client.auth(token=supabase_key)
        return client

    @staticmethod
    def _init_realtime_client(
        realtime_url: str, supabase_key: str
    ) -> supabase_realtime_client.AuthenticatedSupabaseRealtimeClient:
        return supabase_realtime_client.AuthenticatedSupabaseRealtimeClient(realtime_url, supabase_key)

    @staticmethod
    def _init_storage_client(
        storage_url: str,
        headers: typing.Dict[str, str],
        storage_client_timeout: int = storage3.constants.DEFAULT_TIMEOUT,
    ) -> storage3.AsyncStorageClient:
        return storage3.AsyncStorageClient(storage_url, headers, storage_client_timeout)

    def table(self, table_name: str) -> postgrest.AsyncRequestBuilder:  # typing override
        """Perform a table operation.

        Note that the supabase client uses the `from` method, but in Python,
        this is a reserved keyword, so we have elected to use the name `table`.
        Alternatively you can use the `.from_()` method.
        """
        return self.from_(table_name)

    @contextlib.asynccontextmanager
    async def other_postgres_client(self, supabase_url: str = None, supabase_key: str = None, schema: str = "public"):
        other_postgres = None
        try:
            other_postgres = await self.init_other_postgrest_client(
                supabase_url=supabase_url, supabase_key=supabase_key, schema=schema
            )
            yield other_postgres
        finally:
            if other_postgres is not None:
                await other_postgres.aclose()

    async def init_other_postgrest_client(
        self, supabase_url: str = None, supabase_key: str = None, schema: str = "public"
    ) -> postgrest.AsyncPostgrestClient:
        supabase_key = supabase_key or self.supabase_key
        headers = self.options.headers
        if supabase_key != self.supabase_key:
            headers = copy.deepcopy(postgrest.constants.DEFAULT_POSTGREST_CLIENT_HEADERS)
            headers.update(self._format_auth_headers(supabase_key, supabase_key))
        return AuthenticatedAsyncSupabaseClient._init_postgrest_client(
            rest_url=f"{supabase_url}/rest/v1" if supabase_url else self.rest_url,
            supabase_key=supabase_key,
            headers=headers,
            timeout=self.options.postgrest_client_timeout,
            schema=schema,
        )

    async def close(self):
        # timer has to be stopped, there is no public stop api
        if self.auth._refresh_token_timer:
            self.auth._refresh_token_timer.cancel()
            self.auth._refresh_token_timer = None
        try:
            await self.postgrest.aclose()
        except RuntimeError:
            # happens when the event loop is closed already
            pass
        await self.realtime.close()

    def postgres_functions(self):
        return postgres_functions.PostgresFunctions(self.supabase_url, self._get_auth_headers())

    def remove_session_details(self):
        self.auth._remove_session()
        self.auth._notify_all_subscribers("SIGNED_OUT", None)

    def _use_auth_session(self, event: gotrue.AuthChangeEvent, _):
        if event in (
            "SIGNED_IN",
            "SIGNED_OUT",
            "TOKEN_REFRESHED"
        ):
            session = self._get_auth_session()
            auth_token = session.access_token if session else None
            if auth_token:
                self.postgrest.auth(auth_token)
            self.realtime.set_auth(auth_token, self.event_loop)
            # todo uncomment when storage client has to be used by authenticated users instead of anon
            # await self.storage.aclose()
            # self._init_storage_client(self.storage_url, self._get_auth_headers())

    def _get_auth_headers(self):
        """Helper method to get auth headers."""
        # What's the corresponding method to get the token
        return self._format_auth_headers(self.supabase_key, self._get_auth_key())

    def _format_auth_headers(self, supabase_key, auth_token):
        return {
            "apiKey": supabase_key,
            "Authorization": f"Bearer {auth_token}",
        }

    def _get_auth_key(self):
        return self.supabase_key if self._get_auth_session() is None else self._get_auth_session().access_token

    def _get_auth_session(self):
        if self.auth is None:
            # return None when no use is signed in
            return None
        try:
            return self.auth.get_session()
        except gotrue.errors.AuthError:
            return None
