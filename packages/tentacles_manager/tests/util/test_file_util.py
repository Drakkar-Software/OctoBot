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
import datetime
import os
import shutil
import tempfile

import pytest

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util.file_util as file_util


@pytest.fixture
def temp_dir():
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


def test_get_file_creation_time(temp_dir):
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")
    
    result = file_util.get_file_creation_time(test_file)
    
    assert result != ""
    # Verify it's a valid ISO format timestamp
    parsed = datetime.datetime.fromisoformat(result)
    assert parsed.tzinfo == datetime.timezone.utc


def test_get_file_creation_time_nonexistent():
    result = file_util.get_file_creation_time("/nonexistent/file.txt")
    assert result == ""


@pytest.mark.asyncio
async def test_log_tentacles_file_details_with_file(temp_dir):
    test_file = os.path.join(temp_dir, "test_package.zip")
    with open(test_file, "wb") as f:
        f.write(b"test content")
    
    # Should not raise exception
    await file_util.log_tentacles_file_details(test_file, "2024-01-01")


@pytest.mark.asyncio
async def test_log_tentacles_file_details_with_directory(temp_dir):
    subdir = os.path.join(temp_dir, "subdir")
    os.makedirs(subdir)
    with open(os.path.join(temp_dir, "file1.txt"), "w") as f:
        f.write("content1")
    with open(os.path.join(subdir, "file2.txt"), "w") as f:
        f.write("content2")
    
    # Should not raise exception
    await file_util.log_tentacles_file_details(temp_dir, "2024-01-01")


@pytest.mark.asyncio
async def test_find_or_create_directory(temp_dir):
    new_dir = os.path.join(temp_dir, "new_directory")
    
    result = await file_util.find_or_create(new_dir, is_directory=True)
    
    assert result is True
    assert os.path.isdir(new_dir)


@pytest.mark.asyncio
async def test_find_or_create_directory_already_exists(temp_dir):
    os.makedirs(os.path.join(temp_dir, "existing"))
    existing_dir = os.path.join(temp_dir, "existing")
    
    result = await file_util.find_or_create(existing_dir, is_directory=True)
    
    assert result is False


@pytest.mark.asyncio
async def test_find_or_create_file(temp_dir):
    new_file = os.path.join(temp_dir, "new_file.py")
    
    result = await file_util.find_or_create(new_file, is_directory=False, file_content="# init")
    
    assert result is True
    assert os.path.isfile(new_file)
    with open(new_file, "r") as f:
        assert f.read() == "# init"


@pytest.mark.asyncio
async def test_find_or_create_file_already_exists(temp_dir):
    existing_file = os.path.join(temp_dir, "existing.txt")
    with open(existing_file, "w") as f:
        f.write("existing")
    
    result = await file_util.find_or_create(existing_file, is_directory=False)
    
    assert result is False


@pytest.mark.asyncio
async def test_find_or_create_with_empty_init_file_directory(temp_dir):
    new_dir = os.path.join(temp_dir, "new_module")
    
    result = await file_util.find_or_create_with_empty_init_file(new_dir, is_directory=True)
    
    assert result is True
    assert os.path.isdir(new_dir)
    init_file = os.path.join(new_dir, constants.PYTHON_INIT_FILE)
    assert os.path.isfile(init_file)


@pytest.mark.asyncio
async def test_find_or_create_with_empty_init_file_existing_directory_no_init(temp_dir):
    existing_dir = os.path.join(temp_dir, "existing_module")
    os.makedirs(existing_dir)
    
    result = await file_util.find_or_create_with_empty_init_file(existing_dir, is_directory=True)
    
    assert result is True
    init_file = os.path.join(existing_dir, constants.PYTHON_INIT_FILE)
    assert os.path.isfile(init_file)


@pytest.mark.asyncio
async def test_find_or_create_with_empty_init_file_existing_with_init(temp_dir):
    existing_dir = os.path.join(temp_dir, "existing_module")
    os.makedirs(existing_dir)
    init_file = os.path.join(existing_dir, constants.PYTHON_INIT_FILE)
    with open(init_file, "w") as f:
        f.write("")
    
    result = await file_util.find_or_create_with_empty_init_file(existing_dir, is_directory=True)
    
    assert result is False


@pytest.mark.asyncio
async def test_replace_with_remove_or_rename_file(temp_dir):
    source_file = os.path.join(temp_dir, "source.txt")
    dest_file = os.path.join(temp_dir, "dest.txt")
    
    with open(source_file, "w") as f:
        f.write("new content")
    with open(dest_file, "w") as f:
        f.write("old content")
    
    await file_util.replace_with_remove_or_rename(source_file, dest_file)
    
    assert os.path.isfile(dest_file)
    with open(dest_file, "r") as f:
        assert f.read() == "new content"


@pytest.mark.asyncio
async def test_replace_with_remove_or_rename_directory(temp_dir):
    """Test replace_with_remove_or_rename replaces an existing directory."""
    source_dir = os.path.join(temp_dir, "source_dir")
    dest_dir = os.path.join(temp_dir, "dest_dir")
    
    os.makedirs(source_dir)
    with open(os.path.join(source_dir, "file.txt"), "w") as f:
        f.write("new")
    
    os.makedirs(dest_dir)
    with open(os.path.join(dest_dir, "old.txt"), "w") as f:
        f.write("old")
    
    await file_util.replace_with_remove_or_rename(source_dir, dest_dir)
    
    assert os.path.isdir(dest_dir)
    assert os.path.isfile(os.path.join(dest_dir, "file.txt"))
    assert not os.path.isfile(os.path.join(dest_dir, "old.txt"))


@pytest.mark.asyncio
async def test_replace_with_remove_or_rename_new_file(temp_dir):
    source_file = os.path.join(temp_dir, "source.txt")
    dest_file = os.path.join(temp_dir, "new_dest.txt")
    
    with open(source_file, "w") as f:
        f.write("content")
    
    await file_util.replace_with_remove_or_rename(source_file, dest_file)
    
    assert os.path.isfile(dest_file)
    with open(dest_file, "r") as f:
        assert f.read() == "content"


@pytest.mark.asyncio
async def test_copy_with_include_filter_filters_correctly(temp_dir):
    source = os.path.join(temp_dir, "source")
    dest = os.path.join(temp_dir, "dest")
    os.makedirs(source)
    os.makedirs(dest)
    
    # Create files
    with open(os.path.join(source, "include_me.py"), "w") as f:
        f.write("python")
    with open(os.path.join(source, "exclude_me.txt"), "w") as f:
        f.write("text")
    os.makedirs(os.path.join(source, "dist"))
    with open(os.path.join(source, "dist", "bundle.js"), "w") as f:
        f.write("js")
    
    # Also create metadata.json as it's always included
    with open(os.path.join(source, "metadata.json"), "w") as f:
        f.write("{}")
    
    include_patterns = ["*.py", "dist/**/*"]
    
    await file_util.copy_with_include_filter(source, dest, include_patterns)
    
    # Check what was copied
    assert os.path.isfile(os.path.join(dest, "metadata.json")), "metadata.json always included"
    assert os.path.isfile(os.path.join(dest, "include_me.py")), "*.py matched"
    assert os.path.isfile(os.path.join(dest, "dist", "bundle.js")), "dist/**/* matched"
    assert not os.path.isfile(os.path.join(dest, "exclude_me.txt")), "txt should be excluded"


@pytest.mark.asyncio
async def test_copy_with_include_filter_excludes_non_matching_directories(temp_dir):
    """Directories not matching any include pattern prefix must be excluded.
    Reproduces the bug where 'dist/**/*' causes ALL directories to be copied
    because could_match_under_dir returns True for any dir when pattern has '**'.
    """
    source = os.path.join(temp_dir, "source")
    dest = os.path.join(temp_dir, "dest")
    os.makedirs(dest)

    # Simulate the exact node_web_interface layout
    for d in ["dist/assets", "node_modules/some-pkg", "src/components", ".tanstack", "public"]:
        os.makedirs(os.path.join(source, d))
    for f, c in {
        "metadata.json": "{}",
        "__init__.py": "# init",
        "node_web_interface.py": "class NodeWebInterface: pass",
        "dist/index.html": "<html></html>",
        "dist/assets/bundle.js": "// bundle",
        "node_modules/some-pkg/index.js": "// dep",
        "src/components/App.tsx": "// app",
        ".tanstack/config": "config",
        "public/favicon.ico": "icon",
    }.items():
        with open(os.path.join(source, f), "w") as fh:
            fh.write(c)

    include_patterns = ["dist/**/*", "node_web_interface.py"]

    await file_util.copy_with_include_filter(source, dest, include_patterns)

    # Should be present: always-included + matching patterns
    assert os.path.isfile(os.path.join(dest, "metadata.json"))
    assert os.path.isfile(os.path.join(dest, "__init__.py"))
    assert os.path.isfile(os.path.join(dest, "node_web_interface.py"))
    assert os.path.isfile(os.path.join(dest, "dist", "index.html"))
    assert os.path.isfile(os.path.join(dest, "dist", "assets", "bundle.js"))

    # Must NOT be present: directories that don't match "dist/**/*"
    assert not os.path.exists(os.path.join(dest, "node_modules")), \
        "node_modules should be excluded by include filter"
    assert not os.path.exists(os.path.join(dest, "src")), \
        "src should be excluded by include filter"
    assert not os.path.exists(os.path.join(dest, ".tanstack")), \
        ".tanstack should be excluded by include filter"
    assert not os.path.exists(os.path.join(dest, "public")), \
        "public should be excluded by include filter"


@pytest.mark.asyncio
async def test_copy_with_include_filter_always_includes_special_files(temp_dir):
    source = os.path.join(temp_dir, "source")
    dest = os.path.join(temp_dir, "dest")
    os.makedirs(source)
    os.makedirs(dest)
    
    with open(os.path.join(source, "__init__.py"), "w") as f:
        f.write("# init")
    with open(os.path.join(source, "metadata.json"), "w") as f:
        f.write("{}")
    with open(os.path.join(source, "other.txt"), "w") as f:
        f.write("text")
    
    # Very restrictive pattern that wouldn't normally match __init__.py or metadata.json
    include_patterns = ["no_match_pattern"]
    
    await file_util.copy_with_include_filter(source, dest, include_patterns)
    
    assert os.path.isfile(os.path.join(dest, "__init__.py"))
    assert os.path.isfile(os.path.join(dest, "metadata.json"))
    assert not os.path.isfile(os.path.join(dest, "other.txt"))


def test_merge_folders_merges_files(temp_dir):
    source = os.path.join(temp_dir, "source")
    dest = os.path.join(temp_dir, "dest")
    os.makedirs(source)
    os.makedirs(dest)
    
    with open(os.path.join(source, "new_file.txt"), "w") as f:
        f.write("new")
    with open(os.path.join(dest, "existing_file.txt"), "w") as f:
        f.write("existing")
    
    file_util.merge_folders(source, dest)
    
    assert os.path.isfile(os.path.join(dest, "new_file.txt"))
    assert os.path.isfile(os.path.join(dest, "existing_file.txt"))
    with open(os.path.join(dest, "new_file.txt")) as f:
        assert f.read() == "new"


def test_merge_folders_merges_directories_recursively(temp_dir):
    source = os.path.join(temp_dir, "source")
    dest = os.path.join(temp_dir, "dest")
    
    # Create source structure
    os.makedirs(os.path.join(source, "subdir"))
    with open(os.path.join(source, "subdir", "file1.txt"), "w") as f:
        f.write("file1")
    
    # Create dest structure with same subdir
    os.makedirs(os.path.join(dest, "subdir"))
    with open(os.path.join(dest, "subdir", "file2.txt"), "w") as f:
        f.write("file2")
    
    file_util.merge_folders(source, dest)
    
    # Both files should exist in dest/subdir
    assert os.path.isfile(os.path.join(dest, "subdir", "file1.txt"))
    assert os.path.isfile(os.path.join(dest, "subdir", "file2.txt"))


def test_merge_folders_with_ignore_func(temp_dir):
    source = os.path.join(temp_dir, "source")
    dest = os.path.join(temp_dir, "dest")
    os.makedirs(source)
    os.makedirs(dest)
    
    with open(os.path.join(source, "include.txt"), "w") as f:
        f.write("include")
    with open(os.path.join(source, "ignore.txt"), "w") as f:
        f.write("ignore")
    
    def ignore_func(folder, names):
        return {"ignore.txt"}
    
    file_util.merge_folders(source, dest, ignore_func=ignore_func)
    
    assert os.path.isfile(os.path.join(dest, "include.txt"))
    assert not os.path.isfile(os.path.join(dest, "ignore.txt"))


def test_merge_folders_creates_new_subdirectories(temp_dir):
    source = os.path.join(temp_dir, "source")
    dest = os.path.join(temp_dir, "dest")
    
    os.makedirs(os.path.join(source, "new_subdir"))
    with open(os.path.join(source, "new_subdir", "file.txt"), "w") as f:
        f.write("content")
    
    os.makedirs(dest)
    
    file_util.merge_folders(source, dest)
    
    assert os.path.isdir(os.path.join(dest, "new_subdir"))
    assert os.path.isfile(os.path.join(dest, "new_subdir", "file.txt"))
