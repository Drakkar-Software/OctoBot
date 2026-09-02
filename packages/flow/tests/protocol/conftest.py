#  Drakkar-Software OctoBot-Flow
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
# Scoped sys.path guard for protocol wire tests in this folder.
# Those tests import scripts.lib.openapi_compat_lib from packages/protocol/scripts/.
# "scripts" is a generic top-level package name; another scripts directory on
# PYTHONPATH can shadow protocol's copy if protocol is not first on sys.path.
# This conftest is scoped here (not package-wide tests/conftest.py) so path setup
# runs only for protocol wire tests.
# Pytest loads it before test modules, so sys.path.insert(0, protocol_root) wins on
# the first import scripts. The finder checks parent/protocol because protocol is a
# sibling under packages/, not an ancestor of this test path. Does not import scripts
# here — only path setup.

import pathlib
import sys


def _find_protocol_package_root() -> pathlib.Path:
    for parent in pathlib.Path(__file__).resolve().parents:
        for candidate in (parent, parent / "protocol"):
            if candidate.is_dir() and (candidate / "openapi.json").is_file() and (
                candidate / "scripts" / "lib" / "openapi_compat_lib.py"
            ).is_file():
                return candidate
    raise RuntimeError(
        "Could not locate OctoBot packages/protocol for scripts.lib imports"
    )


_protocol_path_string = str(_find_protocol_package_root())
if _protocol_path_string not in sys.path:
    sys.path.insert(0, _protocol_path_string)
