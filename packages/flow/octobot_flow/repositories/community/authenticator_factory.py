import contextlib
import typing

import octobot_flow.entities
import octobot_commons.logging as common_logging
import octobot.community as community
import octobot_flow.repositories.community.initializer as initializer


class CommunityAuthenticatorFactory:
    def __init__(
        self,
        auth_details: octobot_flow.entities.UserAuthentication,
        backend_url: typing.Optional[str] = None,
        anon_key: typing.Optional[str] = None
    ):
        self.auth_details: octobot_flow.entities.UserAuthentication = auth_details
        self.backend_url: typing.Optional[str] = backend_url
        self.anon_key: typing.Optional[str] = anon_key

    def enable_community_authentication(self) -> bool:
        return bool(self.auth_details.has_auth_details() or self.anon_key)

    @contextlib.asynccontextmanager
    async def local_authenticator(self) -> typing.AsyncGenerator[community.CommunityAuthentication, None]:
        if not self.auth_details.email:
            raise ValueError("auth_details.email is required")
        community.IdentifiersProvider.use_production()
        local_instance = None
        configuration = initializer.get_stateless_configuration()
        try:
            local_instance = community.CommunityAuthentication(
                config=configuration, backend_url=self.backend_url, use_as_singleton=False
            )
            local_instance.supabase_client.is_admin = False
            local_instance.silent_auth = self.auth_details.hidden
            # minimal operations: just authenticate
            if self.auth_details.auth_key:
                # auth key authentication
                auth_key = self.auth_details.auth_key
                password = None
            else:
                # password authentication
                password = self.auth_details.password
                auth_key = None
            await local_instance.login(
                self.auth_details.email, password, password_token=None, auth_key=auth_key, minimal=True
            )
            common_logging.get_logger("local_community_user_authenticator").info(
                f"Authenticated as {self.auth_details.email[:3]}[...]{self.auth_details.email[-4:]}"
            )
            yield local_instance
        finally:
            if local_instance is not None:
                await local_instance.logout()
                await local_instance.stop()

    @contextlib.asynccontextmanager
    async def local_anon_authenticator(self) -> typing.AsyncGenerator[community.CommunityAuthentication, None]:
        if not self.anon_key:
            raise ValueError("Anon key is required")
        community.IdentifiersProvider.use_production()
        local_instance = None
        configuration = initializer.get_stateless_configuration()
        try:
            local_instance = community.CommunityAuthentication(
                config=configuration, backend_url=self.backend_url, backend_key=self.anon_key, use_as_singleton=False
            )
            local_instance.supabase_client.is_admin = False
            common_logging.get_logger("local_community_user_authenticator").info(
                f"Authenticated as anonymous user"
            )
            yield local_instance
        finally:
            if local_instance is not None:
                await local_instance.logout()
                await local_instance.stop()
