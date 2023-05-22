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
import typing
import gotrue
import gotrue.errors
import postgrest
import supabase.lib.client_options
import octobot.community.supabase_backend.postgres_functions as postgres_functions


class AuthenticatedAsyncSupabaseClient(supabase.Client):
    """
    supabase.Client subclass to handle:
    - authenticated calls
    - database functions calls
    - auth token refresh
    There should not be OctoBot specific code here
    """
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        options: supabase.lib.client_options.ClientOptions = supabase.lib.client_options.ClientOptions(),
    ):
        self.auth: gotrue.SyncGoTrueClient = None
        self.postgrest: postgrest.AsyncPostgrestClient = None
        super().__init__(supabase_url, supabase_key, options=options)
        # update postgres authentication upon auth state change
        self.auth.on_auth_state_change(self._use_auth_session)

    @staticmethod
    def _init_postgrest_client(
        rest_url: str,
        supabase_key: str,
        headers: typing.Dict[str, str],
        schema: str,
        timeout,    # skip typing to avoid httpx import
    ) -> postgrest.AsyncPostgrestClient:
        """Private helper for creating an instance of the Postgrest client."""
        # Override to use postgrest.AsyncPostgrestClient and allow async requests
        client = postgrest.AsyncPostgrestClient(
            rest_url, headers=headers, schema=schema, timeout=timeout
        )
        client.auth(token=supabase_key)
        return client

    def table(self, table_name: str) -> postgrest.AsyncRequestBuilder:  # typing override
        """Perform a table operation.

        Note that the supabase client uses the `from` method, but in Python,
        this is a reserved keyword, so we have elected to use the name `table`.
        Alternatively you can use the `.from_()` method.
        """
        return self.from_(table_name)

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

    def postgres_functions(self):
        return postgres_functions.PostgresFunctions(self.supabase_url, self._get_auth_headers())

    def _use_auth_session(self, event: gotrue.AuthChangeEvent, _):
        if event in (
            "SIGNED_IN",
            "SIGNED_OUT",
            "TOKEN_REFRESHED"
        ):
            session = self._get_auth_session()
            if session is not None:
                self.postgrest.auth(session.access_token)

    def _get_auth_headers(self):
        """Helper method to get auth headers."""
        # What's the corresponding method to get the token
        return {
            "apiKey": self.supabase_key,
            "Authorization": f"Bearer {self._get_auth_key()}",
        }

    def _get_auth_key(self):
        return self.supabase_key if self._get_auth_session() is None else self._get_auth_session().access_token

    def _get_auth_session(self):
        if self.auth is None:
            return None
        try:
            return self.auth.get_session()
        except gotrue.errors.AuthError:
            return None
