import contextlib
import typing

import octobot_flow.entities
import octobot.community as community
import octobot.community.local_authenticator as local_community_auth


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
        async with local_community_auth.local_user_authenticator(
            email=self.auth_details.email,
            hidden=self.auth_details.hidden,
            backend_url=self.backend_url,
            password=self.auth_details.password if not self.auth_details.auth_key else None,
            auth_key=self.auth_details.auth_key if self.auth_details.auth_key else None,
        ) as local_instance:
            yield local_instance

    @contextlib.asynccontextmanager
    async def local_anon_authenticator(self) -> typing.AsyncGenerator[community.CommunityAuthentication, None]:
        if not self.anon_key:
            raise ValueError("Anon key is required")
        async with local_community_auth.local_anon_user_authenticator(
            backend_url=self.backend_url,
            anon_key=self.anon_key,
        ) as local_instance:
            yield local_instance
