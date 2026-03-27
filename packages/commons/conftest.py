# pylint: disable=missing-module-docstring,missing-function-docstring
import sys
import os


def pytest_addoption(parser):
    parser.addoption(
        "--backend",
        default="python",
        choices=["python", "rust"],
        help="Which octobot_commons backend to test (python or rust)",
    )


# Modules ported to the Rust bridge (mapped to octobot_commons_rs)
_PORTED_MODULES = [
    "octobot_commons",
    "octobot_commons.enums",
    "octobot_commons.constants",
    "octobot_commons.errors",
    "octobot_commons.channels_name",
    "octobot_commons.number_util",
    "octobot_commons.timestamp_util",
    "octobot_commons.time_frame_manager",
    "octobot_commons.list_util",
    "octobot_commons.dict_util",
    "octobot_commons.data_util",
    "octobot_commons.logical_operators",
    "octobot_commons.evaluators_util",
    "octobot_commons.symbols",
    "octobot_commons.symbols.symbol",
    "octobot_commons.symbols.symbol_util",
    "octobot_commons.tree",
    "octobot_commons.tree.base_tree",
    "octobot_commons.logging",
    "octobot_commons.logging.logging_util",
]

# Python-only modules that are NOT ported — stubbed so test collection doesn't crash
_UNPORTED_MODULES = [
    "octobot_commons.aiohttp_util",
    "octobot_commons.async_job",
    "octobot_commons.asyncio_tools",
    "octobot_commons.cache_util",
    "octobot_commons.configuration",
    "octobot_commons.context_util",
    "octobot_commons.cryptography",
    "octobot_commons.databases",
    "octobot_commons.databases.document_database_adaptors",
    "octobot_commons.databases.document_database_adaptors.tinydb_adaptor",
    "octobot_commons.dataclasses",
    "octobot_commons.dsl_interpreter",
    "octobot_commons.dsl_interpreter.operator_parameter",
    "octobot_commons.dsl_interpreter.operators",
    "octobot_commons.dsl_interpreter.operators.re_callable_operator_mixin",
    "octobot_commons.dsl_interpreter.parameters_util",
    "octobot_commons.html_util",
    "octobot_commons.json_util",
    "octobot_commons.logging.context_based_file_handler",
    "octobot_commons.monitored_process",
    "octobot_commons.os_util",
    "octobot_commons.pretty_printer",
    "octobot_commons.profiles",
    "octobot_commons.profiles.profile_data",
    "octobot_commons.profiles.profile_sharing",
    "octobot_commons.signals",
    "octobot_commons.signals.signals_emitter",
    "octobot_commons.singleton",
    "octobot_commons.singleton.singleton_class",
    "octobot_commons.tentacles_management",
    "octobot_commons.tentacles_management.abstract_tentacle",
    "octobot_commons.tentacles_management.class_inspector",
    "octobot_commons.tests",
    "octobot_commons.tests.test_config",
    "octobot_commons.thread_util",
    "octobot_commons.tree.event_tree",
    "octobot_commons.tree.event_provider",
]

# Test directories/files that exclusively test unported modules
_SKIP_TEST_PATHS = [
    # Directories for unported modules
    "tests/configuration/",
    "tests/cryptography/",
    "tests/databases/",
    "tests/dataclasses/",
    "tests/dsl_interpreter/",
    "tests/profiles/",
    "tests/signals/",
    "tests/tentacles_management/",
    # Top-level test files for unported modules
    "tests/test_aiohttp_util.py",
    "tests/test_async_job.py",
    "tests/test_asyncio_tools.py",
    "tests/test_cache_util.py",
    "tests/test_context_util.py",
    "tests/test_html_util.py",
    "tests/test_monitored_process.py",
    "tests/test_os_util.py",
    "tests/test_pretty_printer.py",
    "tests/test_singleton.py",
    "tests/test_data_util.py",
    "tests/test_time_frame_manager.py",
    "tests/thread_util.py",
    # Specific files within partially-ported directories
    "tests/logging/",
    "tests/tree/test_event_tree.py",
]


def pytest_configure(config):
    backend = config.getoption("--backend", default="python")
    os.environ["OCTOBOT_COMMONS_TEST_BACKEND"] = backend
    if backend != "rust":
        return

    import types  # pylint: disable=import-outside-toplevel
    import octobot_commons_rs  # pylint: disable=import-outside-toplevel,import-error

    # Map ported modules
    sys.modules.update({m: octobot_commons_rs for m in _PORTED_MODULES})

    # Set submodule attributes for `from octobot_commons.X import Y` support
    for attr in [
        "constants", "enums", "errors", "channels_name",
        "number_util", "timestamp_util", "time_frame_manager",
        "list_util", "dict_util", "data_util",
        "logical_operators", "evaluators_util",
        "symbols", "tree", "logging",
    ]:
        setattr(octobot_commons_rs, attr, octobot_commons_rs)

    # Stub unported modules so import doesn't crash during collection
    class _Stub(types.ModuleType):
        """Module stub that returns a no-op for any attribute access."""
        def __getattr__(self, name):
            if name.startswith("_"):
                raise AttributeError(name)
            return lambda *a, **kw: None

    for mod_name in _UNPORTED_MODULES:
        if mod_name not in sys.modules:
            stub = _Stub(mod_name)
            stub.__path__ = []  # make it look like a package
            sys.modules[mod_name] = stub


def pytest_ignore_collect(collection_path, config):
    if config.getoption("--backend", default="python") != "rust":
        return False
    try:
        rel = str(collection_path.relative_to(config.rootpath))
    except ValueError:
        return False
    for skip in _SKIP_TEST_PATHS:
        if rel.startswith(skip) or ("/" + skip) in rel:
            return True
    return False


def pytest_collection_modifyitems(config, items):
    if config.getoption("--backend") != "rust":
        return
    import pytest  # pylint: disable=import-outside-toplevel
    skip_rust = pytest.mark.skip(reason="requires Python-only module (not ported to Rust)")
    for item in items:
        rel = str(item.path.relative_to(config.rootpath))
        # Skip entire test files for unported modules
        for skip in _SKIP_TEST_PATHS:
            if rel.startswith(skip):
                item.add_marker(skip_rust)
                break
        else:
            # Skip individual tests needing configuration / numpy / event tree
            if any(n in item.name for n in [
                "load_test_config", "test_get_config",
                "normalize_data", "drop_nan", "shift_value_array",
            ]):
                item.add_marker(skip_rust)
            if any(n in item.nodeid for n in ["test_event_tree", "test_event_provider"]):
                item.add_marker(skip_rust)
