import contextlib
import typing

import octobot.constants as octobot_constants
import octobot.community as community
import octobot_commons.configuration.config_file_manager as config_file_manager
import octobot_commons.configuration
import octobot_commons.logging as common_logging
import octobot_commons.user_root_folder_provider as user_root_folder_provider
import octobot.community.identifiers_provider as identifiers_provider


def _disable_configuration_save(
    configuration: octobot_commons.configuration.Configuration,
) -> octobot_commons.configuration.Configuration:
    configuration.save = lambda *_, **__: None  # type: ignore[method-assign]
    return configuration


def get_stateless_configuration() -> octobot_commons.configuration.Configuration:
    configuration = octobot_commons.configuration.Configuration(None, None)
    configuration.config = {}
    return _disable_configuration_save(configuration)


def get_user_configuration() -> octobot_commons.configuration.Configuration:
    """Load on-disk user config.json so wallet and community settings are available."""
    configuration = octobot_commons.configuration.Configuration(
        config_file_manager.get_user_config(),
        user_root_folder_provider.get_user_profiles_folder(),
        octobot_constants.CONFIG_FILE_SCHEMA,
        octobot_constants.PROFILE_FILE_SCHEMA,
    )
    configuration.read(should_raise=False)
    if configuration.config is None:
        configuration.config = {}
    return _disable_configuration_save(configuration)


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
    configuration = get_user_configuration()
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
