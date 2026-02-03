"""
Pytest configuration for node tests.
Changes working directory to package root for correct static file resolution.
"""
import os
import pytest

# Get the package root (packages/node) from this conftest.py location
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pytest_configure(config):
    """Change working directory to package root before any tests run, required to import tentacles."""
    os.chdir(PACKAGE_ROOT)