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
from pathlib import PurePath

import octobot_tentacles_manager.exporters.artifact_exporter as artifact_exporter
import octobot_tentacles_manager.models as models
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util.tentacle_processing as tentacle_processing


class TentacleExporter(artifact_exporter.ArtifactExporter):
    def __init__(self,
                 artifact: models.Tentacle,
                 tentacles_folder: str,
                 output_dir: str = constants.DEFAULT_EXPORT_DIR,
                 should_cythonize: bool = False,
                 should_zip: bool = False,
                 with_dev_mode: bool = False,
                 use_package_as_file_name: bool = False):
        super().__init__(artifact,
                         tentacles_folder=tentacles_folder,
                         output_dir=output_dir,
                         should_cythonize=should_cythonize,
                         should_zip=should_zip,
                         with_dev_mode=with_dev_mode,
                         use_package_as_file_name=use_package_as_file_name)

    async def prepare_export(self):
        await tentacle_processing.execute_tentacle_build(self.artifact, self.logger)
        
        if not os.path.exists(self.working_folder):
            os.makedirs(self.working_folder)

        # Apply file filtering if include patterns are specified
        if self.artifact.include_patterns:
            await self._copy_with_filtering()
        else:
            # No include patterns - copy everything (default behavior)
            if self.should_zip:
                self.copy_directory_content_to_temporary_dir(self.artifact.tentacle_module_path)
            else:
                self.copy_directory_content_to_working_dir(self.artifact.tentacle_module_path)

    async def _copy_with_filtering(self) -> None:
        include_patterns = self.artifact.include_patterns
        if not isinstance(include_patterns, list):
            include_patterns = [include_patterns]
        
        always_included = constants.ALWAYS_INCLUDED_TENTACLE_FILES
        source_path = self.artifact.tentacle_module_path
        dest_path = self.working_folder
        files_to_copy = set()
        
        for filename in always_included:
            src_file = os.path.join(source_path, filename)
            if os.path.isfile(src_file):
                files_to_copy.add(filename)
        
        for root, dirs, files in os.walk(source_path):
            rel_root = os.path.relpath(root, source_path)
            if rel_root == ".":
                rel_root = ""
            
            for filename in files:
                if rel_root:
                    rel_path = os.path.join(rel_root, filename).replace(os.sep, '/')
                else:
                    rel_path = filename
                
                # Skip always included files (already added)
                if filename in always_included:
                    files_to_copy.add(rel_path)
                    continue
                
                for pattern in include_patterns:
                    pattern = pattern.replace(os.sep, '/')
                    # Use glob-style matching
                    if tentacle_processing.matches_pattern(rel_path, pattern):
                        files_to_copy.add(rel_path)
                        break
        
        for rel_path in files_to_copy:
            src_file = os.path.join(source_path, rel_path.replace('/', os.sep))
            dest_file = os.path.join(dest_path, rel_path.replace('/', os.sep)) 
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            
            if os.path.isfile(src_file):
                import shutil
                shutil.copy2(src_file, dest_file)

    async def after_export(self):
        pass

