#  Drakkar-Software OctoBot-Tentacles-Manager
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import json
import os
import shutil
import tempfile

import pytest

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.managers.tentacle_manager as tentacle_manager
import octobot_tentacles_manager.models as models

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


def _create_tentacle(base_dir, type_path, name, metadata_dict, files=None):
    tentacle_dir = os.path.join(base_dir, type_path, name)
    os.makedirs(tentacle_dir, exist_ok=True)
    with open(os.path.join(tentacle_dir, "metadata.json"), "w") as f:
        json.dump(metadata_dict, f)
    with open(os.path.join(tentacle_dir, "__init__.py"), "w") as f:
        f.write(f"# {name}\n")
    for rel_path, content in (files or {}).items():
        full_path = os.path.join(tentacle_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
    tentacle = models.Tentacle(
        tentacle_root_path=base_dir,
        name=name,
        tentacle_type=models.TentacleType(type_path)
    )
    tentacle.sync_initialize()
    return tentacle


def _collect_files(root_dir):
    result = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            rel = os.path.relpath(os.path.join(root, file), root_dir)
            result.append(rel.replace(os.sep, '/'))
    return sorted(result)


@pytest.fixture
def temp_dirs():
    temp_dir = tempfile.mkdtemp()
    source = os.path.join(temp_dir, "source")
    install = os.path.join(temp_dir, "installed")
    os.makedirs(source)
    os.makedirs(install)
    yield source, install
    shutil.rmtree(temp_dir, ignore_errors=True)


async def test_install_without_include_copies_everything(temp_dirs):
    """Without include patterns, all files are copied."""
    source, install = temp_dirs
    tentacle = _create_tentacle(source, constants.TENTACLES_EVALUATOR_PATH, "Simple", {
        "version": "1.0.0", "origin_package": "Pkg", "tentacles": ["Simple"], "tentacles-requirements": []
    }, {"evaluator.py": "", "helper.py": "", "config/default.json": ""})

    await tentacle_manager.TentacleManager(tentacle).install_tentacle(install)

    installed = _collect_files(os.path.join(install, constants.TENTACLES_EVALUATOR_PATH, "Simple"))
    assert set(installed) == {"__init__.py", "metadata.json", "evaluator.py", "helper.py", "config/default.json"}


async def test_install_with_include_filters_files(temp_dirs):
    """Include patterns filter to only matching files + always-included files."""
    source, install = temp_dirs
    tentacle = _create_tentacle(source, "Services/Interfaces", "NodeTentacle", {
        "version": "1.0.0", "origin_package": "Pkg", "tentacles": ["NodeTentacle"],
        "tentacles-requirements": [], "include": ["dist/**/*", "node_tentacle.py"]
    }, {
        "node_tentacle.py": "",
        "dist/index.html": "", "dist/assets/bundle.js": "",
        # Should be excluded
        "package.json": "", "src/app.ts": "", "node_modules/pkg/index.js": "",
    })

    await tentacle_manager.TentacleManager(tentacle).install_tentacle(install)

    installed = _collect_files(os.path.join(install, "Services", "Interfaces", "NodeTentacle"))
    # Included: always-included + pattern matches
    assert set(installed) == {
        "__init__.py", "metadata.json", "node_tentacle.py",
        "dist/index.html", "dist/assets/bundle.js",
    }
