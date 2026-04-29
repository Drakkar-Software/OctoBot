import typing

import octobot.community
import octobot_flow.errors
import octobot_flow.repositories.community.community_repository as community_repository_import


def ensure_is_authenticated(
    maybe_authenticator: typing.Optional[octobot.community.CommunityAuthentication]
) -> octobot.community.CommunityAuthentication:
    if maybe_authenticator and maybe_authenticator.is_logged_in():
        return maybe_authenticator
    raise octobot_flow.errors.CommunityAuthenticationRequiredError(
        "Community authentication is required to fetch custom actions"
    )


def ensure_authenticated_community_repository(
    maybe_community_repository: typing.Optional[community_repository_import.CommunityRepository]
) -> community_repository_import.CommunityRepository:
    if maybe_community_repository is not None and ensure_is_authenticated(maybe_community_repository.authenticator):
        return maybe_community_repository
    raise octobot_flow.errors.CommunityAuthenticationRequiredError(
        "Community authentication is required to use the community repository"
    )
