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
import os
import shutil

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
