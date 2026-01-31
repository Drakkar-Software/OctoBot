"""
Pytest configuration for tentacles_manager tests.
Changes working directory to OctoBot root for file access.
Overrides TENTACLES_PATH to use test-specific location to avoid conflicts with root tentacles.
Mocks version to return 'unknown' for consistent test behavior.
"""
import os
import sys
import pytest
from unittest import mock

# Get the test directory and package root from this conftest.py location
TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
PACKAGE_ROOT = os.path.dirname(TESTS_ROOT)
OCTOBOT_ROOT = os.path.dirname(os.path.dirname(PACKAGE_ROOT))

# Add OctoBot root to sys.path for package imports
if OCTOBOT_ROOT not in sys.path:
    sys.path.insert(0, OCTOBOT_ROOT)

# Test-specific tentacles path (relative to OCTOBOT_ROOT)
TEST_TENTACLES_PATH = os.path.join("packages", "tentacles_manager", "tests", "tentacles")

# Override TENTACLES_PATH constant BEFORE any tests import it
import octobot_tentacles_manager.constants as constants
constants.TENTACLES_PATH = TEST_TENTACLES_PATH

# Add the parent of tests to sys.path so 'tests' module can be imported
# This makes 'from tests.api import ...' work
TESTS_PARENT = os.path.dirname(TESTS_ROOT)  # packages/tentacles_manager/
if TESTS_PARENT not in sys.path:
    sys.path.insert(0, TESTS_PARENT)

# Add the tests directory to sys.path so 'tentacles' module can be imported
# This makes 'import tentacles' work when tentacles are installed to tests/tentacles/
if TESTS_ROOT not in sys.path:
    sys.path.insert(0, TESTS_ROOT)


def pytest_configure(config):
    """Change working directory to OctoBot root before any tests run."""
    os.chdir(OCTOBOT_ROOT)


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
