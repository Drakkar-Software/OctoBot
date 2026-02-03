"""
Pytest configuration for OctoBot tests.
Sets up correct paths for test module imports.
"""
import os
import sys
import pytest

# Get the OctoBot root from this conftest.py location
OCTOBOT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
TEST_UTILS_ROOT = os.path.join(TESTS_ROOT, "test_utils")
PACKAGES_TENTACLES_ROOT = os.path.join(OCTOBOT_ROOT, "packages", "tentacles")

# Add OctoBot root to sys.path so 'import tentacles' works
if OCTOBOT_ROOT not in sys.path:
    sys.path.insert(0, OCTOBOT_ROOT)

# Add tests root to sys.path so 'from tests.test_utils import ...' works
if TESTS_ROOT not in sys.path:
    sys.path.insert(0, TESTS_ROOT)

# Add test_utils root to sys.path so 'from config import ...' works
if TEST_UTILS_ROOT not in sys.path:
    sys.path.insert(0, TEST_UTILS_ROOT)


def pytest_configure(config):
    """Change working directory to OctoBot root before any tests run."""
    os.chdir(OCTOBOT_ROOT)
    
    # Set up tentacles path - check if tentacles exists as symlink or directory
    tentacles_link = os.path.join(OCTOBOT_ROOT, "tentacles")
    
    # Try to create symlink if tentacles doesn't exist but packages/tentacles does
    if not os.path.exists(tentacles_link) and os.path.exists(PACKAGES_TENTACLES_ROOT):
        try:
            os.symlink(PACKAGES_TENTACLES_ROOT, tentacles_link)
        except OSError:
            pass  # May fail in sandbox
    
    # Patch tentacles manager constants to use packages/tentacles path
    try:
        import octobot_tentacles_manager.constants as tm_constants
        if os.path.exists(PACKAGES_TENTACLES_ROOT):
            tm_constants.TENTACLES_PATH = PACKAGES_TENTACLES_ROOT
    except ImportError:
        pass
