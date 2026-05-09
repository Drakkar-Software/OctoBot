"""
Pytest configuration for additional_tests.
Tests marked @pytest.mark.slow require live exchange credentials and are skipped
by default. Pass --run-slow (or set RUN_SLOW_TESTS=1) to enable them.

Mirrors the Rust integration tests' #[ignore = "requires live credentials"] pattern.
"""
import os

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run tests marked as slow (require live exchange credentials)",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: requires live exchange credentials")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-slow") or os.environ.get("RUN_SLOW_TESTS"):
        return
    skip_slow = pytest.mark.skip(reason="requires live credentials (use --run-slow)")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
