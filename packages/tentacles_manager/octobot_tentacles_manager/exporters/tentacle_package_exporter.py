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
import asyncio
import os

import aiofiles
import octobot_commons.logging as logging
import octobot_commons.constants as commons_constants
try:
    import yaml
except ImportError:
    if commons_constants.USE_MINIMAL_LIBS:
        # mock yaml imports
        class YamlImportMock:
            def safe_load(self, *args):
                raise ImportError("yaml not installed")
        yaml = YamlImportMock()
    else:
        raise

import octobot_tentacles_manager.exporters.artifact_exporter as artifact_exporter
import octobot_tentacles_manager.models as models
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util as util
import octobot_tentacles_manager.util.tentacle_processing as tentacle_processing


class TentaclePackageExporter(artifact_exporter.ArtifactExporter):
    def __init__(self,
                 artifact: models.TentaclePackage,
                 exported_tentacles_package: str,
                 tentacles_folder: str,
                 output_dir: str = constants.DEFAULT_EXPORT_DIR,
                 should_cythonize: bool = False,
                 should_zip: bool = False,
                 with_dev_mode: bool = False,
                 metadata_file: str = None,
                 use_package_as_file_name: bool = False):
        output_dir = TentaclePackageExporter.include_output_dir_in_package_name_if_any(artifact, output_dir)
        super().__init__(artifact,
                         tentacles_folder=tentacles_folder,
                         output_dir=output_dir,
                         should_cythonize=should_cythonize,
                         should_zip=should_zip,
                         with_dev_mode=with_dev_mode,
                         use_package_as_file_name=use_package_as_file_name)
        self.exported_tentacles_package: str = exported_tentacles_package
        self.should_cleanup_working_folder: bool = True
        self.imported_metadata_file: str = metadata_file

        self.tentacles_filter: util.TentacleFilter = None
        self.tentacles_white_list: list = []
        self.tentacles = []

        if self.should_zip:
            self.working_folder = os.path.join(self.working_folder, constants.TENTACLES_ARCHIVE_ROOT)

    async def prepare_export(self):
        if not self.with_dev_mode or self.exported_tentacles_package is not None:
            self.tentacles = util.load_tentacle_with_metadata(self.tentacles_folder)
            # remove dev-mode or non exported package tentacles if necessary
            self.tentacles_white_list = util.filter_tentacles_by_dev_mode_and_package(
                tentacles=self.tentacles,
                with_dev_mode=self.with_dev_mode,
                package_filter=self.exported_tentacles_package
            )

        # Execute build commands for tentacles that have them
        for tentacle in (self.tentacles_white_list or []):
            if tentacle.build_command:
                await tentacle_processing.execute_tentacle_build(tentacle, self.logger)

        # filter tentacles
        self.tentacles_filter = util.TentacleFilter(self.tentacles, self.tentacles_white_list)

        # set white list tentacles as TentaclePackage.artifacts
        self.artifact.artifacts = self.tentacles_white_list

        if self.should_zip:
            self.copy_directory_content_to_temporary_dir(self.tentacles_folder,
                                                         ignore=self.tentacles_filter.should_ignore)
        else:
            self.copy_directory_content_to_working_dir(self.tentacles_folder,
                                                       ignore=self.tentacles_filter.should_ignore)

    @staticmethod
    def include_output_dir_in_package_name_if_any(artifact: models.TentaclePackage, output_dir: str) -> str:
        """
        Include artifact output_path in output_dir if any
        :return: final output_dir
        """
        if artifact.output_path:
            return os.path.join(output_dir, artifact.output_path) \
                if output_dir != constants.CURRENT_DIR_PATH else artifact.output_path
        return output_dir

    async def after_export(self):
        pass

    def get_metadata_file_path(self) -> str:
        """
        :return: the metadata destination file path
        """
        return os.path.abspath(self.output_dir)

    async def get_metadata_instance(self) -> models.ArtifactMetadata:
        metadata_instance = models.MetadataFactory(self.artifact).create_metadata_instance()
        if self.imported_metadata_file:
            async with aiofiles.open(os.path.join(self.imported_metadata_file), "r") as imported_metadata_file:
                metadata_instance.original_metadata_dict = yaml.safe_load(await imported_metadata_file.read())
            metadata_instance.load_from_dict()
        return metadata_instance
