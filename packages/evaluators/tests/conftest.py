"""
Pytest configuration for evaluators tests.
Changes working directory to OctoBot root for tentacles access.
"""
import os
import sys
import pytest

# Get the OctoBot root and package root from this conftest.py location
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCTOBOT_ROOT = os.path.dirname(os.path.dirname(PACKAGE_ROOT))

# Add OctoBot root to sys.path for tentacles imports
if OCTOBOT_ROOT not in sys.path:
    sys.path.insert(0, OCTOBOT_ROOT)


def pytest_configure(config):
    """Change working directory to OctoBot root before any tests run."""
    os.chdir(OCTOBOT_ROOT)

