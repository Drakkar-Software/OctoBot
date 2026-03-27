# pylint: disable=missing-module-docstring,missing-function-docstring
import sys
import os

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--backend",
        default="python",
        choices=["python", "rust"],
        help="Which octobot_evaluators backend to test (python or rust)",
    )


def pytest_configure(config):
    backend = config.getoption("--backend", default="python")
    os.environ["OCTOBOT_EVALUATORS_TEST_BACKEND"] = backend
    if backend != "rust":
        return

    import octobot_evaluators_rs  # pylint: disable=import-outside-toplevel,import-error

    # Build a separate enums module that wraps the Rust _enums submodule.
    # Python tests do `from octobot_evaluators.enums import EvaluatorMatrixTypes`
    # which is a Python enum.Enum -- the Rust crate exposes these via _enums.
    import types  # pylint: disable=import-outside-toplevel

    _enums_mod = types.ModuleType("octobot_evaluators.enums")
    _enums_mod.__dict__.update(octobot_evaluators_rs._enums.__dict__)  # noqa: WPS437
    _enums_mod.__package__ = "octobot_evaluators"

    # Map every submodule path that the Python package exposes.
    # All submodules point to octobot_evaluators_rs since the Rust module
    # exports everything at the top level, except enums which use _enums.
    submodules = {
        # top-level package
        "octobot_evaluators": octobot_evaluators_rs,
        # leaf modules
        "octobot_evaluators.constants": octobot_evaluators_rs,
        "octobot_evaluators.enums": _enums_mod,
        "octobot_evaluators.errors": octobot_evaluators_rs,
        # matrix subtree
        "octobot_evaluators.matrix": octobot_evaluators_rs,
        "octobot_evaluators.matrix.matrix": octobot_evaluators_rs,
        "octobot_evaluators.matrix.matrices": octobot_evaluators_rs,
        "octobot_evaluators.matrix.matrix_manager": octobot_evaluators_rs,
        "octobot_evaluators.matrix.channel": octobot_evaluators_rs,
        "octobot_evaluators.matrix.channel.matrix": octobot_evaluators_rs,
        # evaluators subtree
        "octobot_evaluators.evaluators": octobot_evaluators_rs,
        "octobot_evaluators.evaluators.channel": octobot_evaluators_rs,
        "octobot_evaluators.evaluators.channel.evaluator_channel": octobot_evaluators_rs,
        "octobot_evaluators.evaluators.channel.evaluators": octobot_evaluators_rs,
    }
    sys.modules.update(submodules)

    # Python's import system also checks parent module attributes
    # for `import octobot_evaluators.matrix as matrix` to work.
    octobot_evaluators_rs.constants = octobot_evaluators_rs
    octobot_evaluators_rs.enums = _enums_mod
    octobot_evaluators_rs.errors = octobot_evaluators_rs
    octobot_evaluators_rs.matrix = octobot_evaluators_rs
    octobot_evaluators_rs.evaluators = octobot_evaluators_rs
    octobot_evaluators_rs.channel = octobot_evaluators_rs


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests that require the install_tentacles fixture when
    running against the Rust backend (tentacles are not available)."""
    if config.getoption("--backend", default="python") != "rust":
        return

    skip_marker = pytest.mark.skip(
        reason="install_tentacles fixture not available with --backend=rust"
    )
    for item in items:
        if "install_tentacles" in getattr(item, "fixturenames", ()):
            item.add_marker(skip_marker)
