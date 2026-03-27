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
    import types  # pylint: disable=import-outside-toplevel

    # Build a separate enums module that wraps the Rust _enums submodule.
    # Python tests do `from octobot_evaluators.enums import EvaluatorMatrixTypes`
    # which is a Python enum.Enum -- the Rust crate exposes these via _enums.
    _enums_mod = types.ModuleType("octobot_evaluators.enums")
    _enums_mod.__dict__.update(octobot_evaluators_rs._enums.__dict__)  # noqa: WPS437
    _enums_mod.__package__ = "octobot_evaluators"

    # Lightweight reimplementation of evaluation_util functions used by tests.
    # Cannot load the real module because it transitively imports numpy/databases.
    _eval_util_mod = types.ModuleType("octobot_evaluators.util.evaluation_util")
    _eval_util_mod.__package__ = "octobot_evaluators.util"

    def _get_eval_time(full_candle=None, time_frame=None, partial_candle=None, kline=None):
        from octobot_commons.enums import PriceIndexes, TimeFramesMinutes, TimeFrames as TF
        from octobot_commons.constants import MINUTE_TO_SECONDS
        if full_candle is not None and time_frame is not None:
            return (full_candle[PriceIndexes.IND_PRICE_TIME.value]
                    + TimeFramesMinutes[TF(time_frame)] * MINUTE_TO_SECONDS)
        if partial_candle is not None:
            return partial_candle[PriceIndexes.IND_PRICE_TIME.value]
        if kline is not None:
            return kline[PriceIndexes.IND_PRICE_TIME.value]
        raise ValueError("Invalid arguments")

    def _get_shortest_time_frame(ideal_time_frame, preferred_available_time_frames, others):
        from octobot_commons.time_frame_manager import sort_time_frames
        if ideal_time_frame in preferred_available_time_frames:
            return ideal_time_frame
        if preferred_available_time_frames:
            return sort_time_frames(preferred_available_time_frames)[0]
        return sort_time_frames(others)[0]

    _eval_util_mod.get_eval_time = _get_eval_time
    _eval_util_mod.get_shortest_time_frame = _get_shortest_time_frame

    _util_mod = types.ModuleType("octobot_evaluators.util")
    _util_mod.__package__ = "octobot_evaluators"
    _util_mod.evaluation_util = _eval_util_mod

    # Stub class for unported modules — returns a no-op for any attribute access
    class _Stub(types.ModuleType):
        def __getattr__(self, name):
            if name.startswith("_"):
                raise AttributeError(name)
            return lambda *a, **kw: None

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
        # api subtree
        "octobot_evaluators.api": octobot_evaluators_rs,
        "octobot_evaluators.api.evaluators": octobot_evaluators_rs,
        "octobot_evaluators.api.matrix": octobot_evaluators_rs,
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
        # util subtree (Python-side, not Rust)
        "octobot_evaluators.util": _util_mod,
        "octobot_evaluators.util.evaluation_util": _eval_util_mod,
    }

    # Stub unported modules so import doesn't crash during collection
    _unported = [
        "octobot_evaluators.api.initialization",
        "octobot_evaluators.evaluators.evaluator_factory",
    ]
    for mod_name in _unported:
        stub = _Stub(mod_name)
        stub.__path__ = []
        submodules[mod_name] = stub

    sys.modules.update(submodules)

    # Python's import system also checks parent module attributes
    # for `import octobot_evaluators.matrix as matrix` to work.
    octobot_evaluators_rs.constants = octobot_evaluators_rs
    octobot_evaluators_rs.enums = _enums_mod
    octobot_evaluators_rs.errors = octobot_evaluators_rs
    octobot_evaluators_rs.api = octobot_evaluators_rs
    octobot_evaluators_rs.matrix = octobot_evaluators_rs
    octobot_evaluators_rs.evaluators = octobot_evaluators_rs
    octobot_evaluators_rs.channel = octobot_evaluators_rs
    octobot_evaluators_rs.util = _util_mod


_SKIP_TEST_PATHS = [
    "tests/evaluators/channel/test_evaluator_channel.py",
    "tests/evaluators/test_evaluator_factory.py",
    "tests/evaluators/test_evaluator_factory_create_evaluators.py",
    "tests/matrix/channel/test_matrix.py",
]


def pytest_ignore_collect(collection_path, config):
    if config.getoption("--backend", default="python") != "rust":
        return False
    try:
        rel = str(collection_path.relative_to(config.rootpath))
    except ValueError:
        return False
    for skip in _SKIP_TEST_PATHS:
        if rel == skip or rel.endswith("/" + skip):
            return True
    return False


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
