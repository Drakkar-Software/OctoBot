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
from __future__ import annotations
import asyncio
import os
from typing import TYPE_CHECKING

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.enums as enums
import octobot_tentacles_manager.creators as tentacle_creator
import octobot_tentacles_manager.exporters as exporters
import octobot_tentacles_manager.models as models
import octobot_tentacles_manager.util as util
import octobot_tentacles_manager.api.uploader as uploader_api
import octobot_commons.logging as logging

if TYPE_CHECKING:
    from octobot_tentacles_manager.exporters import TentacleBundleExporter


def start_tentacle_creator(config, commands) -> int:
    tentacle_creator_inst = tentacle_creator.TentacleCreator(config)
    return tentacle_creator_inst.parse_commands(commands)


async def create_tentacles_package(package_name: str,
                                   tentacles_folder: str = constants.TENTACLES_PATH,
                                   output_dir: str = constants.DEFAULT_EXPORT_DIR,
                                   exported_tentacles_package: str = None,
                                   uploader_type: str = enums.UploaderTypes.S3.value,
                                   in_zip: bool = True,
                                   with_dev_mode: bool = False,
                                   use_package_as_file_name: bool = False,
                                   upload_details: list = None,
                                   metadata_file: str = None,
                                   cythonize: bool = False) -> int:
    tentacle_package: models.TentaclePackage = models.TentaclePackage(package_name)
    export_result: int = await exporters.TentaclePackageExporter(artifact=tentacle_package,
                                                                 tentacles_folder=tentacles_folder,
                                                                 exported_tentacles_package=exported_tentacles_package,
                                                                 output_dir=output_dir,
                                                                 should_zip=in_zip,
                                                                 with_dev_mode=with_dev_mode,
                                                                 metadata_file=metadata_file,
                                                                 use_package_as_file_name=use_package_as_file_name,
                                                                 should_cythonize=cythonize).export()
    if upload_details is not None and len(upload_details) > 0:
        export_path: str = tentacle_package.output_path
        alias_name: str = os.path.join(tentacle_package.version, os.path.basename(export_path))
        metadata_file: str = os.path.join(os.path.dirname(export_path), constants.ARTIFACT_METADATA_FILE)
        await uploader_api.upload_file_or_folder(uploader_type=uploader_type,
                                                 path=upload_details[0],
                                                 artifact_path=export_path,
                                                 artifact_alias=alias_name)
        await uploader_api.upload_file_or_folder(uploader_type=uploader_type,
                                                 path=upload_details[0],
                                                 artifact_path=metadata_file,
                                                 artifact_alias=os.path.join(tentacle_package.version,
                                                                             constants.ARTIFACT_METADATA_FILE))
    return export_result


async def create_all_tentacles_bundle(output_dir: str = constants.DEFAULT_EXPORT_DIR,
                                      tentacles_folder: str = constants.TENTACLES_PATH,
                                      exported_tentacles_package: str = None,
                                      uploader_type: str = enums.UploaderTypes.S3.value,
                                      in_zip: bool = True,
                                      with_dev_mode: bool = False,
                                      cythonize: bool = False,
                                      should_remove_artifacts_after_use: bool = False,
                                      use_package_as_file_name: bool = False,
                                      upload_url: str = None,
                                      should_zip_bundle: bool = False) -> int:
    logger = logging.get_logger("TentacleManagerApi")
    error_count: int = 0
    tentacle_bundle_exported_list = []
    tentacles: list = util.load_tentacle_with_metadata(tentacles_folder)
    tentacles_white_list = util.filter_tentacles_by_dev_mode_and_package(
        tentacles=tentacles,
        with_dev_mode=with_dev_mode,
        package_filter=exported_tentacles_package
    )
    for tentacle in tentacles_white_list:
        try:
            tentacle_package = models.TentaclePackage()
            tentacle_exporter = exporters.TentacleExporter(artifact=tentacle,
                                                           output_dir=output_dir,
                                                           tentacles_folder=tentacles_folder,
                                                           should_zip=in_zip,
                                                           with_dev_mode=with_dev_mode,
                                                           should_cythonize=cythonize,
                                                           use_package_as_file_name=use_package_as_file_name)
            await tentacle_exporter.export()
            tentacle_package.add_artifact(tentacle)
            tentacle_bundle_exporter = exporters.TentacleBundleExporter(
                artifact=tentacle_package,
                tentacles_folder=tentacles_folder,
                output_dir=output_dir,
                should_zip=should_zip_bundle,
                should_remove_artifacts_after_use=should_remove_artifacts_after_use,
                use_package_as_file_name=use_package_as_file_name)
            await tentacle_bundle_exporter.export()
            tentacle_bundle_exported_list.append(tentacle_bundle_exporter)
        except Exception as e:
            logger.error(f"Error when exporting tentacle {tentacle.name} : {str(e)}")
            error_count += 1

    if upload_url is not None:
        await asyncio.gather(
            *[_upload_exported_tentacle_bundle(upload_url, exported_tentacle_bundle, uploader_type)
              for exported_tentacle_bundle in tentacle_bundle_exported_list])

    return error_count


async def _upload_exported_tentacle_bundle(upload_url: str,
                                           exported_tentacle_bundle: TentacleBundleExporter,
                                           uploader_type: str):
    export_path = exported_tentacle_bundle.artifact.output_path
    alias_path = os.path.basename(export_path)
    if constants.ARTIFACT_VERSION_SEPARATOR in export_path:
        alias_name, alias_version = alias_path.split(constants.ARTIFACT_VERSION_SEPARATOR)
        alias_path = f"{alias_name}/{alias_version}"
    await uploader_api.upload_file_or_folder(uploader_type=uploader_type,
                                             path=upload_url,
                                             artifact_path=export_path,
                                             artifact_alias=alias_path)
