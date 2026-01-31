"""
Pytest configuration for commons tests.
Changes working directory to package root for correct static file resolution.
"""
import os
import sys
import pytest

# Get the package root (packages/commons) from this conftest.py location
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))

# Add the package root to sys.path so 'tests' module can be imported
# This makes 'from tests.profiles import ...' work
if PACKAGE_ROOT not in sys.path:
    sys.path.insert(0, PACKAGE_ROOT)

# Add the tests directory to sys.path so 'tests' module can be imported
if TESTS_ROOT not in sys.path:
    sys.path.insert(0, TESTS_ROOT)


def pytest_configure(config):
    """Change working directory to package root before any tests run."""
    os.chdir(PACKAGE_ROOT)
