import contextlib
import typing

import octobot.community as community
import octobot_commons.configuration
import octobot_commons.logging as common_logging
import octobot.community.identifiers_provider as identifiers_provider


def get_stateless_configuration() -> octobot_commons.configuration.Configuration:
    configuration = octobot_commons.configuration.Configuration(None, None)
    configuration.config = {}
    # disable save
    configuration.save = lambda *_, **__: _ # type: ignore
    return configuration

@contextlib.asynccontextmanager
async def local_user_authenticator(
    email: typing.Optional[str] = None,
    hidden: typing.Optional[bool] = None,
    backend_url: typing.Optional[str] = None,
    password: typing.Optional[str] = None,
    auth_key: typing.Optional[str] = None,
) -> typing.AsyncGenerator["community.CommunityAuthentication", None]:
    community.IdentifiersProvider.use_production()
    local_instance = None
    configuration = get_stateless_configuration()
    authenticate = password or auth_key
    if authenticate and not email:
        raise ValueError("email is required when authenticating with password or auth_key")
    try:
        local_instance = community.CommunityAuthentication(
            config=configuration, backend_url=backend_url, use_as_singleton=False
        )
        local_instance.supabase_client.is_admin = False
        local_instance.silent_auth = False if hidden is None else hidden
        if auth_key:
            password_value = None
            auth_key_value = auth_key
        else:
            password_value = password
            auth_key_value = None
        if authenticate:
            email = typing.cast(str, email) # email is always str here
            await local_instance.login(
                email, password_value, password_token=None, auth_key=auth_key_value, minimal=True
            )
            auth_logger = common_logging.get_logger("local_community_user_authenticator")
            auth_logger.info(f"Authenticated as {email[:3]}[...]{email[-4:]}")
        yield local_instance
    finally:
        if local_instance is not None:
            if authenticate:
                await local_instance.logout()
            await local_instance.stop()


@contextlib.asynccontextmanager
async def local_anon_user_authenticator(
    backend_url: typing.Optional[str] = None,
    anon_key: typing.Optional[str] = None,
) -> typing.AsyncGenerator["community.CommunityAuthentication", None]:
    anon_key = anon_key or identifiers_provider.IdentifiersProvider.BACKEND_KEY
    community.IdentifiersProvider.use_production()
    local_instance = None
    configuration = get_stateless_configuration()
    try:
        local_instance = community.CommunityAuthentication(
            config=configuration, backend_url=backend_url, backend_key=anon_key, use_as_singleton=False
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
