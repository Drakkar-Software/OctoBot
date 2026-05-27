import contextlib

import mock
import pytest

import octobot.community.local_authenticator as local_community_auth


@contextlib.contextmanager
def mocked_local_user_configuration():
    with mock.patch.object(
        local_community_auth,
        "get_user_configuration",
        local_community_auth.get_stateless_configuration,
    ):
        yield


@pytest.fixture(autouse=True)
def _mock_local_user_configuration():
    with mocked_local_user_configuration():
        yield
