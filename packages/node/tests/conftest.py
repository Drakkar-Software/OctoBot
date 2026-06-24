import contextlib
import os

import mock
import pytest

_TESTS_RUN_OCTOBOT_PROCESS_WAITING_TIME_SECONDS = 2

os.environ.setdefault(
    "RUN_OCTOBOT_PROCESS_WAITING_TIME_SECONDS",
    str(_TESTS_RUN_OCTOBOT_PROCESS_WAITING_TIME_SECONDS),
)

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


@pytest.fixture(autouse=True)
def _fast_run_octobot_process_recall(monkeypatch):
    import octobot_node.constants as node_constants

    monkeypatch.setattr(
        node_constants,
        "RUN_OCTOBOT_PROCESS_WAITING_TIME_SECONDS",
        _TESTS_RUN_OCTOBOT_PROCESS_WAITING_TIME_SECONDS,
    )
