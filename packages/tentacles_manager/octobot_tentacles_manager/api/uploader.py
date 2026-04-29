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

import octobot_tentacles_manager.uploaders.nexus_uploader as nexus_uploader
import octobot_tentacles_manager.uploaders.s3_uploader as s3_uploader
import octobot_tentacles_manager.enums as enums
import octobot_tentacles_manager.util as util


async def upload_file_or_folder(uploader_type: str, path: str, artifact_path: str, artifact_alias: str = None) -> int:
    await util.log_tentacles_file_details(artifact_path, util.get_file_creation_time(artifact_path))
    if uploader_type == enums.UploaderTypes.S3.value:
        return await upload_file_or_folder_to_s3(s3_path=path,
                                                 artifact_path=artifact_path,
                                                 artifact_alias=artifact_alias)
    elif uploader_type == enums.UploaderTypes.NEXUS.value:
        return await upload_file_or_folder_to_nexus(nexus_path=path,
                                                    artifact_path=artifact_path,
                                                    artifact_alias=artifact_alias)
    else:
        raise ValueError("Unknown uploader type")


async def upload_file_or_folder_to_nexus(nexus_path: str, artifact_path: str, artifact_alias: str = None) -> int:
    if os.path.isfile(artifact_path):
        return await upload_file_to_nexus(nexus_path=nexus_path,
                                          file_path=artifact_path,
                                          alias_file_name=artifact_alias)
    elif os.path.isdir(artifact_path):
        return await upload_folder_to_nexus(nexus_path=nexus_path,
                                            folder_path=artifact_path,
                                            alias_folder_name=artifact_alias)


async def upload_file_to_nexus(nexus_path: str, file_path: str, alias_file_name: str = None) -> int:
    uploader: nexus_uploader.NexusUploader = nexus_uploader.NexusUploader()
    upload_result: int = await uploader.upload_file(upload_path=nexus_path,
                                                    file_path=file_path,
                                                    destination_file_name=alias_file_name)
    await uploader.close_session()
    return upload_result


async def upload_folder_to_nexus(nexus_path: str, folder_path: str, alias_folder_name: str = None) -> int:
    uploader: nexus_uploader.NexusUploader = nexus_uploader.NexusUploader()
    upload_result: int = await uploader.upload_folder(upload_path=nexus_path,
                                                      folder_path=folder_path,
                                                      destination_folder_name=alias_folder_name)
    await uploader.close_session()
    return upload_result


async def upload_file_or_folder_to_s3(s3_path: str, artifact_path: str, artifact_alias: str = None) -> int:
    if os.path.isfile(artifact_path):
        return await upload_file_to_s3(s3_path=s3_path,
                                       file_path=artifact_path,
                                       alias_file_name=artifact_alias)
    elif os.path.isdir(artifact_path):
        return await upload_folder_to_s3(s3_path=s3_path,
                                         folder_path=artifact_path,
                                         alias_folder_name=artifact_alias)


async def upload_file_to_s3(s3_path: str, file_path: str, alias_file_name: str = None) -> int:
    uploader: s3_uploader.S3Uploader = s3_uploader.S3Uploader()
    upload_result: int = await uploader.upload_file(upload_path=s3_path,
                                                    file_path=file_path,
                                                    destination_file_name=alias_file_name)
    return upload_result


async def upload_folder_to_s3(s3_path: str, folder_path: str, alias_folder_name: str = None) -> int:
    uploader: s3_uploader.S3Uploader = s3_uploader.S3Uploader()
    upload_result: int = await uploader.upload_folder(upload_path=s3_path,
                                                      folder_path=folder_path,
                                                      destination_folder_name=alias_folder_name)
    return upload_result
