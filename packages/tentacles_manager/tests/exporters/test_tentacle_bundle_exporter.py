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
import yaml

import octobot_tentacles_manager.models as models
import octobot_tentacles_manager.exporters as exporters
import octobot_tentacles_manager.util as util
import octobot_tentacles_manager.constants as constants
from octobot_tentacles_manager.api import create_tentacles_package
from tests.api import install_tentacles, TENTACLE_PACKAGE  # pants: no-infer-dep

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_tentacle_bundle_exporter_for_each_tentacle(install_tentacles):
    # Export each tentacle in a bundle
    for tentacle in util.load_tentacle_with_metadata(constants.TENTACLES_PATH):
        tentacle_package = models.TentaclePackage()
        await exporters.TentacleExporter(artifact=tentacle, should_zip=True,
                                         tentacles_folder=constants.TENTACLES_PATH,
                                         use_package_as_file_name=True).export()
        tentacle_package.add_artifact(tentacle)
        await exporters.TentacleBundleExporter(
            artifact=tentacle_package,
            tentacles_folder=constants.TENTACLES_PATH,
            use_package_as_file_name=True).export()

    # Check if each tentacle bundle has been generated
    # check files count
    output_files = os.listdir(constants.DEFAULT_EXPORT_DIR)
    assert len(output_files) == 22
    assert "daily_trading_mode.zip" in output_files
    assert "generic_exchange_importer@1.2.0" in output_files
    assert "other_instant_fluctuations_evaluator@1.2.0" in output_files
    assert "mixed_strategies_evaluator.zip" in output_files
    assert "mixed_strategies_evaluator" not in output_files


async def test_tentacle_bundle_exporter_for_an_unique_bundle_containing_all_tentacles(install_tentacles):
    # Export all tentacles and generate a bundle containing all
    tentacle_package = models.TentaclePackage()
    for tentacle in util.load_tentacle_with_metadata(constants.TENTACLES_PATH):
        await exporters.TentacleExporter(artifact=tentacle, should_zip=True,
                                         tentacles_folder=constants.TENTACLES_PATH,
                                         use_package_as_file_name=True).export()
        tentacle_package.add_artifact(tentacle)
    await exporters.TentacleBundleExporter(
        artifact=tentacle_package,
        tentacles_folder=constants.TENTACLES_PATH,
        should_remove_artifacts_after_use=True,
        use_package_as_file_name=True).export()

    # Check if the final bundle contains all exported tentacles and a metadata file
    # check files count
    output_files = os.listdir(constants.DEFAULT_EXPORT_DIR)
    assert len(output_files) == 1
    exported_bundle_path = os.path.join(constants.DEFAULT_EXPORT_DIR, output_files[0])
    output_files = os.listdir(exported_bundle_path)
    assert len(output_files) == 12
    assert "daily_trading_mode.zip" in output_files
    assert "generic_exchange_importer@1.2.0_package" not in output_files
    assert "other_instant_fluctuations_evaluator@1.2.0_package" not in output_files
    assert "mixed_strategies_evaluator.zip" in output_files
    assert "mixed_strategies_evaluator" not in output_files
    assert constants.ARTIFACT_METADATA_FILE in output_files

    # test multiple tentacle bundle metadata
    with open(os.path.join(exported_bundle_path, constants.ARTIFACT_METADATA_FILE)) as metadata_file:
        metadata_content = yaml.safe_load(metadata_file.read())
        assert metadata_content[constants.ARTIFACT_METADATA_ARTIFACT_TYPE] == "tentacle_package"
        assert len(metadata_content[constants.ARTIFACT_METADATA_TENTACLES]) == 11
        assert "forum_evaluator@1.2.0" in metadata_content[constants.ARTIFACT_METADATA_TENTACLES]


async def test_tentacle_bundle_exporter_with_specified_output_dir(install_tentacles):
    specified_output_dir = "out/dir/test"
    # Export each tentacle in a bundle in a specified output dir
    for tentacle in util.load_tentacle_with_metadata(constants.TENTACLES_PATH):
        tentacle_package = models.TentaclePackage()
        await exporters.TentacleExporter(artifact=tentacle,
                                         should_zip=True,
                                         output_dir=specified_output_dir,
                                         tentacles_folder=constants.TENTACLES_PATH,
                                         use_package_as_file_name=True).export()
        tentacle_package.add_artifact(tentacle)
        await exporters.TentacleBundleExporter(
            artifact=tentacle_package,
            output_dir=specified_output_dir,
            tentacles_folder=constants.TENTACLES_PATH,
            use_package_as_file_name=True).export()

    # Check if each tentacle bundle has been generated in the specified directory
    output_files = os.listdir(specified_output_dir)
    assert len(output_files) == 22
    assert "daily_trading_mode.zip" in output_files
    assert "generic_exchange_importer@1.2.0" in output_files
    shutil.rmtree(specified_output_dir)


async def test_tentacle_bundle_exporter_with_metadata_injection(install_tentacles):
    assert await create_tentacles_package(package_name=TENTACLE_PACKAGE,
                                          output_dir=constants.CURRENT_DIR_PATH,
                                          metadata_file=os.path.join("tests", "static", "metadata.yml"),
                                          in_zip=True,
                                          use_package_as_file_name=True) == 0
    assert os.path.exists(constants.ARTIFACT_METADATA_FILE)
    with open(constants.ARTIFACT_METADATA_FILE) as metadata_file:
        metadata_content = yaml.safe_load(metadata_file.read())
        assert metadata_content[constants.ARTIFACT_METADATA_ARTIFACT_TYPE] == "tentacle_package"
        assert len(metadata_content[constants.ARTIFACT_METADATA_TENTACLES]) == 11
        assert "forum_evaluator@1.2.0" in metadata_content[constants.ARTIFACT_METADATA_TENTACLES]
        assert metadata_content[constants.ARTIFACT_METADATA_NAME] == "test-full"
        assert metadata_content[constants.ARTIFACT_METADATA_AUTHOR] == "DrakkarSoftware"
        assert metadata_content[constants.ARTIFACT_METADATA_REPOSITORY] == "TEST-TM"
        assert metadata_content[constants.ARTIFACT_METADATA_VERSION] == "1.5.57"



async def test_metadata_build_and_include_parsing():
    temp_dir = tempfile.mkdtemp()
    
    try:
        # ===== Test 1: Tentacle WITHOUT build and include =====
        evaluator_dir = os.path.join(temp_dir, constants.TENTACLES_EVALUATOR_PATH)
        simple_path = os.path.join(evaluator_dir, "SimpleTentacle")
        os.makedirs(simple_path)
        
        simple_metadata = {
            "version": "1.0.0",
            "origin_package": "Test-Package",
            "tentacles": ["SimpleTentacle"],
            "tentacles-requirements": []
        }
        
        with open(os.path.join(simple_path, "metadata.json"), "w") as f:
            json.dump(simple_metadata, f)
        with open(os.path.join(simple_path, "__init__.py"), "w") as f:
            f.write("# Simple tentacle\n")
        with open(os.path.join(simple_path, "simple.py"), "w") as f:
            f.write("class SimpleTentacle:\n    pass\n")
        
        simple_tentacle = models.Tentacle(
            tentacle_root_path=temp_dir,
            name="SimpleTentacle",
            tentacle_type=models.TentacleType(constants.TENTACLES_EVALUATOR_PATH)
        )
        simple_tentacle.tentacle_module_path = simple_path
        simple_tentacle.sync_initialize()
        
        # Verify build_command and include_patterns are None
        assert simple_tentacle.build_command is None, "build_command should be None when not in metadata"
        assert simple_tentacle.include_patterns is None, "include_patterns should be None when not in metadata"
        
        # Export and verify all files are included (no filtering)
        exporter = exporters.TentacleExporter(
            artifact=simple_tentacle,
            tentacles_folder=temp_dir,
            should_zip=False,
            use_package_as_file_name=True
        )
        result = await exporter.export()
        assert result == 0, "Export should succeed"
        
        export_path = simple_tentacle.output_path
        exported_files = []
        for root, dirs, files in os.walk(export_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), export_path)
                exported_files.append(rel_path)
        
        assert "metadata.json" in exported_files
        assert "__init__.py" in exported_files
        assert "simple.py" in exported_files, "All files should be included when no include patterns"
        
        # ===== Test 2: Tentacle WITH build and include =====
        advanced_path = os.path.join(evaluator_dir, "AdvancedTentacle")
        os.makedirs(advanced_path)
        
        build_commands = ["npm install", "npm run build"]
        include_patterns = ["dist/**/*", "*.js", "README.md"]
        
        advanced_metadata = {
            "version": "2.0.0",
            "origin_package": "Test-Package",
            "tentacles": ["AdvancedTentacle"],
            "tentacles-requirements": [],
            "build": build_commands,
            "include": include_patterns
        }
        
        with open(os.path.join(advanced_path, "metadata.json"), "w") as f:
            json.dump(advanced_metadata, f)
        with open(os.path.join(advanced_path, "__init__.py"), "w") as f:
            f.write("# Advanced tentacle\n")
        
        advanced_tentacle = models.Tentacle(
            tentacle_root_path=temp_dir,
            name="AdvancedTentacle",
            tentacle_type=models.TentacleType(constants.TENTACLES_EVALUATOR_PATH)
        )
        advanced_tentacle.tentacle_module_path = advanced_path
        advanced_tentacle.sync_initialize()
        
        # Verify build_command and include_patterns were properly parsed
        assert advanced_tentacle.build_command == build_commands, "build_command should match metadata"
        assert advanced_tentacle.include_patterns == include_patterns, "include_patterns should match metadata"
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(constants.DEFAULT_EXPORT_DIR):
            shutil.rmtree(constants.DEFAULT_EXPORT_DIR, ignore_errors=True)


@pytest.fixture
def setup_package_with_build_and_include_tentacle():
    temp_dir = tempfile.mkdtemp()
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)

    tentacles_dir = os.path.join(temp_dir, "tentacles")

    # Create Services/Interfaces/node_test_tentacle (with build + include)
    node_tentacle_path = os.path.join(tentacles_dir, "Services", "Interfaces", "node_test_tentacle")
    os.makedirs(node_tentacle_path)
    metadata_with_build = {
        "version": "1.0.0",
        "origin_package": "Test-Package",
        "tentacles": ["NodeTestTentacle"],
        "tentacles-requirements": [],
        "build": ["mkdir -p dist", "echo 'built content' > dist/bundle.js"],
        "include": ["dist/**/*", "node_test_tentacle.py"]
    }
    with open(os.path.join(node_tentacle_path, "metadata.json"), "w") as f:
        json.dump(metadata_with_build, f)
    with open(os.path.join(node_tentacle_path, "__init__.py"), "w") as f:
        f.write("# Node test tentacle\n")
    with open(os.path.join(node_tentacle_path, "node_test_tentacle.py"), "w") as f:
        f.write("class NodeTestTentacle:\n    pass\n")
    # Files/dirs that should be EXCLUDED by include patterns
    with open(os.path.join(node_tentacle_path, "package.json"), "w") as f:
        f.write('{"name": "test"}')
    os.makedirs(os.path.join(node_tentacle_path, "src"))
    with open(os.path.join(node_tentacle_path, "src", "app.ts"), "w") as f:
        f.write("// source code\n")
    os.makedirs(os.path.join(node_tentacle_path, "node_modules", "some-pkg"))
    with open(os.path.join(node_tentacle_path, "node_modules", "some-pkg", "index.js"), "w") as f:
        f.write("// dependency\n")

    simple_tentacle_path = os.path.join(tentacles_dir, "Evaluator", "simple_test_tentacle")
    os.makedirs(simple_tentacle_path)
    metadata_simple = {
        "version": "1.0.0",
        "origin_package": "Test-Package",
        "tentacles": ["SimpleTestTentacle"],
        "tentacles-requirements": []
    }
    with open(os.path.join(simple_tentacle_path, "metadata.json"), "w") as f:
        json.dump(metadata_simple, f)
    with open(os.path.join(simple_tentacle_path, "__init__.py"), "w") as f:
        f.write("# Simple tentacle\n")
    with open(os.path.join(simple_tentacle_path, "simple_evaluator.py"), "w") as f:
        f.write("class SimpleTestTentacle:\n    pass\n")
    with open(os.path.join(simple_tentacle_path, "helper.py"), "w") as f:
        f.write("# helper module\n")

    yield tentacles_dir, output_dir, node_tentacle_path, simple_tentacle_path

    shutil.rmtree(temp_dir, ignore_errors=True)
    if os.path.exists(constants.TENTACLES_PACKAGE_CREATOR_TEMP_FOLDER):
        shutil.rmtree(constants.TENTACLES_PACKAGE_CREATOR_TEMP_FOLDER, ignore_errors=True)


async def test_package_exporter_build_command_execution(setup_package_with_build_and_include_tentacle):
    tentacles_dir, output_dir, node_tentacle_path, simple_tentacle_path = \
        setup_package_with_build_and_include_tentacle

    tentacle_package = models.TentaclePackage("test-package")
    exporter = exporters.TentaclePackageExporter(
        artifact=tentacle_package,
        tentacles_folder=tentacles_dir,
        exported_tentacles_package=None,
        output_dir=output_dir,
        should_zip=False,
        with_dev_mode=False,
    )
    result = await exporter.export()
    assert result == 0, "Export should succeed"

    # Build output should have been created in the SOURCE directory
    dist_file = os.path.join(node_tentacle_path, "dist", "bundle.js")
    assert os.path.exists(dist_file), \
        f"Build command should create dist/bundle.js in source dir. Files: {os.listdir(node_tentacle_path)}"
    with open(dist_file) as f:
        assert "built content" in f.read()


async def test_package_exporter_include_filtering(setup_package_with_build_and_include_tentacle):
    tentacles_dir, output_dir, node_tentacle_path, simple_tentacle_path = \
        setup_package_with_build_and_include_tentacle

    tentacle_package = models.TentaclePackage("test-package")
    exporter = exporters.TentaclePackageExporter(
        artifact=tentacle_package,
        tentacles_folder=tentacles_dir,
        exported_tentacles_package=None,
        output_dir=output_dir,
        should_zip=False,
        with_dev_mode=False,
    )
    result = await exporter.export()
    assert result == 0, "Export should succeed"

    # Check the node_test_tentacle in the output
    exported_node_tentacle = os.path.join(
        exporter.working_folder, "Services", "Interfaces", "node_test_tentacle"
    )
    assert os.path.isdir(exported_node_tentacle), \
        f"node_test_tentacle should exist in output. Contents: {os.listdir(exporter.working_folder)}"

    # Collect all files in the exported node tentacle
    exported_files = []
    for root, dirs, files in os.walk(exported_node_tentacle):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), exported_node_tentacle)
            exported_files.append(rel_path.replace(os.sep, '/'))

    # Files that MUST be included (always-included + matching include patterns)
    assert "metadata.json" in exported_files, "metadata.json should always be included"
    assert "__init__.py" in exported_files, "__init__.py should always be included"
    assert "node_test_tentacle.py" in exported_files, "node_test_tentacle.py matches include pattern"
    assert "dist/bundle.js" in exported_files, "dist/bundle.js matches dist/**/* pattern"

    # Files that MUST be excluded
    assert "package.json" not in exported_files, "package.json should NOT be included"
    assert not any("src" in f for f in exported_files), "src/ directory should NOT be included"
    assert not any("node_modules" in f for f in exported_files), "node_modules/ should NOT be included"


async def test_package_exporter_no_include_keeps_all(setup_package_with_build_and_include_tentacle):
    tentacles_dir, output_dir, node_tentacle_path, simple_tentacle_path = \
        setup_package_with_build_and_include_tentacle

    tentacle_package = models.TentaclePackage("test-package")
    exporter = exporters.TentaclePackageExporter(
        artifact=tentacle_package,
        tentacles_folder=tentacles_dir,
        exported_tentacles_package=None,
        output_dir=output_dir,
        should_zip=False,
        with_dev_mode=False,
    )
    result = await exporter.export()
    assert result == 0, "Export should succeed"

    # Check the simple_test_tentacle in the output (no include patterns)
    exported_simple_tentacle = os.path.join(
        exporter.working_folder, "Evaluator", "simple_test_tentacle"
    )
    assert os.path.isdir(exported_simple_tentacle), \
        f"simple_test_tentacle should exist in output"

    exported_files = []
    for root, dirs, files in os.walk(exported_simple_tentacle):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), exported_simple_tentacle)
            exported_files.append(rel_path.replace(os.sep, '/'))

    # ALL files should be present (no filtering)
    assert "metadata.json" in exported_files
    assert "__init__.py" in exported_files
    assert "simple_evaluator.py" in exported_files
    assert "helper.py" in exported_files, "All files should be kept when no include patterns"


async def test_wildcard_patterns():
    """Test edge cases with various wildcard patterns like *.py and **/*.js"""
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create tentacle with wildcard patterns
        evaluator_dir = os.path.join(temp_dir, constants.TENTACLES_EVALUATOR_PATH)
        tentacle_path = os.path.join(evaluator_dir, "WildcardTentacle")
        os.makedirs(tentacle_path)
        
        # Create metadata with wildcard patterns
        metadata = {
            "version": "1.0.0",
            "origin_package": "Test-Package",
            "tentacles": ["WildcardTentacle"],
            "tentacles-requirements": [],
            "include": ["*.py", "config/*.json", "**/*.md"]  # Various patterns
        }
        
        with open(os.path.join(tentacle_path, "metadata.json"), "w") as f:
            json.dump(metadata, f)
        with open(os.path.join(tentacle_path, "__init__.py"), "w") as f:
            f.write("# init\n")
        
        # Top-level .py files (should match *.py)
        with open(os.path.join(tentacle_path, "main.py"), "w") as f:
            f.write("# main\n")
        
        # config/*.json (should match config/*.json)
        config_dir = os.path.join(tentacle_path, "config")
        os.makedirs(config_dir)
        with open(os.path.join(config_dir, "settings.json"), "w") as f:
            f.write("{}\n")
        
        # Nested .md files (should match **/*.md)
        docs_dir = os.path.join(tentacle_path, "docs", "api")
        os.makedirs(docs_dir)
        with open(os.path.join(docs_dir, "README.md"), "w") as f:
            f.write("# Docs\n")
        
        # Files that should NOT match
        with open(os.path.join(tentacle_path, "data.txt"), "w") as f:
            f.write("data\n")
        sub_dir = os.path.join(tentacle_path, "utils")
        os.makedirs(sub_dir)
        with open(os.path.join(sub_dir, "helper.py"), "w") as f:  # *.py only matches top-level
            f.write("# helper\n")
        
        # Export using TentacleExporter
        tentacle = models.Tentacle(
            tentacle_root_path=temp_dir,
            name="WildcardTentacle",
            tentacle_type=models.TentacleType(constants.TENTACLES_EVALUATOR_PATH)
        )
        tentacle.tentacle_module_path = tentacle_path
        tentacle.sync_initialize()
        
        exporter = exporters.TentacleExporter(
            artifact=tentacle,
            tentacles_folder=temp_dir,
            should_zip=False,
            use_package_as_file_name=True
        )
        result = await exporter.export()
        assert result == 0
        
        # Collect exported files
        export_path = tentacle.output_path
        exported_files = []
        for root, dirs, files in os.walk(export_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), export_path)
                exported_files.append(rel_path.replace(os.sep, '/'))
        
        # Verify matches
        assert "metadata.json" in exported_files  # Always included
        assert "__init__.py" in exported_files  # Always included
        assert "main.py" in exported_files, "*.py should match top-level .py files"
        assert "config/settings.json" in exported_files, "config/*.json should match"
        assert "docs/api/README.md" in exported_files, "**/*.md should match nested .md files"
        
        # Verify non-matches
        assert "data.txt" not in exported_files, "data.txt should not match any pattern"
        assert "utils/helper.py" not in exported_files, "*.py should not match nested .py files"
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(constants.DEFAULT_EXPORT_DIR):
            shutil.rmtree(constants.DEFAULT_EXPORT_DIR, ignore_errors=True)

