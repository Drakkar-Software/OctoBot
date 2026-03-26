# pylint: disable=missing-module-docstring,missing-function-docstring
import sys
import os


def pytest_addoption(parser):
    parser.addoption(
        "--backend",
        default="python",
        choices=["python", "rust"],
        help="Which async_channel backend to test (python or rust)",
    )


def pytest_configure(config):
    backend = config.getoption("--backend", default="python")
    os.environ["ASYNC_CHANNEL_TEST_BACKEND"] = backend
    if backend != "rust":
        return

    import async_channel_rs  # pylint: disable=import-outside-toplevel,import-error

    # Map every submodule path that the Python package exposes.
    # All submodules point to async_channel_rs since the Rust module
    # exports everything at the top level.
    submodules = {
        "async_channel": async_channel_rs,
        "async_channel.constants": async_channel_rs,
        "async_channel.enums": async_channel_rs,
        "async_channel.consumer": async_channel_rs,
        "async_channel.producer": async_channel_rs,
        "async_channel.channels": async_channel_rs,
        "async_channel.channels.channel": async_channel_rs,
        "async_channel.channels.channel_instances": async_channel_rs,
        "async_channel.util": async_channel_rs,
        "async_channel.util.channel_creator": async_channel_rs,
        "async_channel.util.logging_util": async_channel_rs,
    }
    sys.modules.update(submodules)

    # Python's import system also checks parent module attributes
    # for `import async_channel.channels as channels` to work.
    async_channel_rs.constants = async_channel_rs
    async_channel_rs.enums = async_channel_rs
    async_channel_rs.consumer = async_channel_rs
    async_channel_rs.producer = async_channel_rs
    async_channel_rs.channels = async_channel_rs
    async_channel_rs.util = async_channel_rs
