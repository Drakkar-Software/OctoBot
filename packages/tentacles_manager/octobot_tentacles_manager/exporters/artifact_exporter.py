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

import abc
import os
import os.path as path
import shutil

import aiofiles
import octobot_commons.logging as logging
import octobot_commons.constants as commons_constants
try:
    import yaml
except ImportError:
    if commons_constants.USE_MINIMAL_LIBS:
        # mock yaml imports
        class YamlImportMock:
            def dump(self, *args):
                raise ImportError("yaml not installed")
        yaml = YamlImportMock()
    else:
        raise

import octobot_tentacles_manager.models as models
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.creators as creators
import octobot_tentacles_manager.managers as managers
import octobot_tentacles_manager.util as util


class ArtifactExporter:
    __metaclass__ = abc.ABCMeta

    def __init__(self,
                 artifact: models.Artifact,
                 tentacles_folder: str,
                 output_dir: str = constants.DEFAULT_EXPORT_DIR,
                 should_cythonize: bool = False,
                 should_zip: bool = False,
                 with_dev_mode: bool = False,
                 use_package_as_file_name: bool = False):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.artifact = artifact
        self.tentacles_folder: str = tentacles_folder
        self.output_dir: str = output_dir if output_dir is not None else constants.DEFAULT_EXPORT_DIR

        self.should_cleanup_working_folder: bool = False
        self.should_cythonize = should_cythonize
        self.should_zip = should_zip
        self.with_dev_mode = with_dev_mode
        self.use_package_as_file_name = use_package_as_file_name

        self.artifact.output_dir = self.output_dir
        self.artifact.output_path = os.path.join(self.output_dir, self.artifact.name)
        self.working_folder = constants.TENTACLES_PACKAGE_CREATOR_TEMP_FOLDER \
            if self.should_zip else self.artifact.output_path

    @abc.abstractmethod
    async def prepare_export(self):
        """
        Called before export process, should be implemented if necessary
        :return: None
        """
        raise NotImplementedError("prepare_export is not implemented")

    @abc.abstractmethod
    async def get_metadata_instance(self) -> models.ArtifactMetadata:
        """
        Called after prepare_export, should be implemented if a metadata file has to be created
        :return: an ArtifactMetadata instance
        """
        raise NotImplementedError("get_metadata_instance is not implemented")

    @abc.abstractmethod
    async def after_export(self) -> None:
        """
        Called after export process, should be implemented if necessary
        :return: None
        """
        raise NotImplementedError("after_export is not implemented")

    async def export(self) -> int:
        """
        Run artifact export process by calling :
        - export preparation with abstract prepare_export()
        - create metadata file if necessary
        - export cleanup, cythonization and compression with cleanup_cythonize_and_archive_if_necessary()
        - export finalization with abstract after_export()
        :return: an error code as integer (0 for success and 1 for fail)
        """
        try:
            await self.prepare_export()
            await self.create_metadata_file()
            await self.cleanup_cythonize_and_archive_if_necessary()
            await self.after_export()
            return 0
        except Exception as e:
            self.logger.exception(e, True, f"Error while performing {self.artifact.ARTIFACT_NAME} export : {e}")
            return 1

    async def cleanup_cythonize_and_archive_if_necessary(self) -> None:
        """
        Perform cleanup, cythonization and compression if necessary
        :return: None
        """
        if self.should_cleanup_working_folder:
            await self.cleanup_working_folder()

        # handle tentacles cythonization if required
        if self.should_cythonize:
            await creators.cythonize_and_compile_tentacles(self.working_folder)

        # Zip if required
        if self.should_zip:
            self.artifact.output_path = self.zip_temporary_folder()
            self.logger.info(f"Zipped {self.artifact.ARTIFACT_NAME} available at: {self.artifact.output_path}")
        else:
            self.artifact.output_path = os.path.abspath(self.working_folder)
            self.logger.info(f"Cleaned {self.artifact.ARTIFACT_NAME} available at: {self.artifact.output_path}")

    async def cleanup_working_folder(self) -> None:
        """
        Clean working folder from tentacle file architecture and non tentacle files
        :return: None
        """
        # cleanup temp working folder
        tentacles_setup_manager = managers.TentaclesSetupManager(self.working_folder)
        await tentacles_setup_manager.remove_tentacle_arch_init_files()
        util.remove_unnecessary_files(self.working_folder)

        # remove non tentacles files before zipping
        if self.should_zip:
            util.remove_non_tentacles_files(self.working_folder, self.logger)

    @staticmethod
    def create_or_replace_temporary_creator_dir() -> None:
        """
        Remove temporary creator directory if exists and create it
        :return:
        """
        if path.exists(constants.TENTACLES_PACKAGE_CREATOR_TEMP_FOLDER):
            shutil.rmtree(constants.TENTACLES_PACKAGE_CREATOR_TEMP_FOLDER)

    def copy_directory_content_to_temporary_dir(self, folder_to_copy: str, ignore=None) -> None:
        """
        Copy a directory content to creator temporary dir
        :param folder_to_copy: the folder to copy content
        :param ignore: shutil ignoring file pattern
        :return: None
        """
        self.create_or_replace_temporary_creator_dir()
        shutil.copytree(folder_to_copy, self.working_folder, ignore=ignore)

    def copy_directory_content_to_working_dir(self, folder_to_copy: str, ignore=None) -> None:
        """
        Copy a directory content to working dir
        :param folder_to_copy: the folder to copy content
        :param ignore: shutil ignoring file pattern
        :return: None
        """
        if not path.exists(self.working_folder):
            shutil.copytree(folder_to_copy, self.working_folder, ignore=ignore)
        else:
            util.merge_folders(folder_to_copy, self.working_folder, ignore)

    def zip_temporary_folder(self) -> str:
        """
        Archive creator temporary dir to a zip file
        :return: the path of the archive
        """
        zipped_file = shutil.make_archive(
            os.path.abspath(os.path.join(self.artifact.output_dir, self.get_zip_file_name())),
            constants.TENTACLES_PACKAGE_FORMAT,
            constants.TENTACLES_PACKAGE_CREATOR_TEMP_FOLDER
        )
        try:
            # remove working folder
            shutil.rmtree(constants.TENTACLES_PACKAGE_CREATOR_TEMP_FOLDER)
        except Exception as e:
            self.logger.error(f"Error when cleaning up temporary folder: {e}")
        return zipped_file

    def get_zip_file_name(self) -> str:
        """
        Set package name using artifact name or platform data when cythonized and remove .zip extension if necessary
        :return: the zip file name
        """
        return self.get_exported_file_name().split(f".{constants.TENTACLES_PACKAGE_FORMAT}")[0]. \
            replace(constants.ARTIFACT_VERSION_SEPARATOR, "_")

    def get_exported_file_name(self) -> str:
        """
        return: the export file name depending on compilation and self.use_package_as_file_name value
        """
        if self.use_package_as_file_name:
            return self.artifact.name
        if self.should_cythonize:
            return f"{util.get_os_str()}_{util.get_arch_str()}"
        return constants.ANY_PLATFORM_FILE_NAME

    def get_metadata_file_path(self) -> str:
        """
        :return: the metadata destination file path
        """
        return os.path.abspath(self.working_folder)

    async def create_metadata_file(self) -> None:
        """
        Creates metadata file from artifacts count
        :return: None
        """
        try:
            artifact_metadata: models.ArtifactMetadata = await self.get_metadata_instance()
            metadata_path = path.join(self.get_metadata_file_path(),
                                      constants.ARTIFACT_METADATA_FILE)
            os.makedirs(path.dirname(metadata_path), exist_ok=True)
            async with aiofiles.open(metadata_path, "w") as metadata_file:
                await metadata_file.write(yaml.dump(artifact_metadata.to_dict()))
        except NotImplementedError:
            pass  # Metadata file creation is ignored
