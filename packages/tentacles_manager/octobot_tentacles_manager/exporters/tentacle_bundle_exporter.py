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

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.exporters.artifact_exporter as artifact_exporter
import octobot_tentacles_manager.models as models
import octobot_tentacles_manager.util as util


class TentacleBundleExporter(artifact_exporter.ArtifactExporter):
    def __init__(self,
                 artifact: models.TentaclePackage,
                 tentacles_folder: str,
                 output_dir: str = constants.DEFAULT_EXPORT_DIR,
                 should_zip: bool = False,
                 should_remove_artifacts_after_use: bool = False,
                 use_package_as_file_name: bool = False):
        super().__init__(artifact,
                         tentacles_folder=tentacles_folder,
                         output_dir=output_dir,
                         should_cythonize=False,
                         should_zip=should_zip,
                         with_dev_mode=False,
                         use_package_as_file_name=use_package_as_file_name)
        self.should_remove_artifacts_after_use: bool = should_remove_artifacts_after_use

    async def prepare_export(self):
        if not os.path.exists(self.working_folder):
            os.makedirs(self.working_folder)

        for artifact in self.artifact.artifacts:
            # copy artifact content
            if os.path.isfile(artifact.output_path):
                shutil.copyfile(artifact.output_path, os.path.join(self.working_folder,
                                                                   os.path.basename(artifact.output_path)))
            else:
                if self.should_zip:
                    self.copy_directory_content_to_temporary_dir(artifact.output_path)
                else:
                    self.copy_directory_content_to_working_dir(artifact.output_path)

    async def after_export(self) -> None:
        """
        Remove artifacts origin file or folder after bundling if necessary
        :return: None
        """
        if self.should_remove_artifacts_after_use:
            for artifact in self.artifact.artifacts:
                util.remove_dir_or_file_from_path(artifact.output_path)

    async def get_metadata_instance(self) -> models.ArtifactMetadata:
        if len(self.artifact.artifacts) == 1:
            return models.MetadataFactory(self.artifact.artifacts[0]).create_metadata_instance()
        return models.MetadataFactory(self.artifact).create_metadata_instance()
