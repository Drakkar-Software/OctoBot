import os
import pytest

# Get the package root directory
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pytest_configure(config):
    """Change working directory to package root before any tests run."""
    os.chdir(PACKAGE_ROOT)
