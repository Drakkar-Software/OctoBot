import pytest
import mock
import octobot_tentacles_manager.constants as constants

@pytest.fixture(autouse=True)
def mock_bot_version():
    """
    Mock _get_installation_context_bot_version to return 'unknown'.
    This ensures consistent test behavior between monorepo and standalone package.
    In monorepo, octobot.constants.LONG_VERSION is available (returns actual version).
    In standalone, it's not (returns 'unknown').
    Tests were written for standalone behavior.
    """
    from octobot_tentacles_manager.configuration import tentacles_setup_configuration
    with mock.patch.object(
        tentacles_setup_configuration.TentaclesSetupConfiguration,
        '_get_installation_context_bot_version',
        return_value=constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION_UNKNOWN
    ):
        yield


@pytest.fixture(autouse=True)
def allow_unsigned_test_tentacles(request):
    """
    Test zip fixtures are not signed with the Drakkar key.
    Allow unsigned tentacles globally so tests focus on install/export logic
    rather than signature verification (which has dedicated tests).
    Tests marked with @pytest.mark.signature_verification opt out.
    """
    if "signature_verification" in request.keywords:
        yield
    else:
        with mock.patch.object(constants, "ALLOW_UNSIGNED_TENTACLES", True):
            yield
