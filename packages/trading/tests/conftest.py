"""
Pytest configuration for trading tests.
Changes working directory to package root for correct static file resolution.
"""
import os
import sys
import pytest

# Get the package root (packages/trading) from this conftest.py location
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the package root to sys.path IMMEDIATELY at module level
# This allows imports like 'from tests.exchanges import ...' to work
if PACKAGE_ROOT not in sys.path:
    sys.path.insert(0, PACKAGE_ROOT)


def pytest_configure(config):
    """Change working directory to package root before any tests run."""
    os.chdir(PACKAGE_ROOT)
