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
