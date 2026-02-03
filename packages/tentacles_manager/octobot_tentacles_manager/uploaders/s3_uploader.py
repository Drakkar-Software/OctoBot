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
import octobot_commons.constants as commons_constants
try:
    import aioboto3
except ImportError:
    if commons_constants.USE_MINIMAL_LIBS:
        # mock aioboto3 imports
        class Aioboto3ImportMock:
            class Session:
                def __init__(self, *args):
                    raise ImportError("aioboto3 not installed")
        aioboto3 = Aioboto3ImportMock()
    else:
        raise
import logging

import octobot_tentacles_manager.uploaders.uploader as uploader


class S3Uploader(uploader.Uploader):
    ENV_S3_API_KEY = "S3_API_KEY"
    ENV_S3_API_SECRET_KEY = "S3_API_SECRET_KEY"
    ENV_S3_ENDPOINT_URL = "S3_ENDPOINT_URL"
    ENV_S3_BUCKET_NAME = "S3_BUCKET_NAME"
    ENV_S3_REGION_NAME = "S3_REGION_NAME"

    S3_BOTO_KEY = "s3"

    def __init__(self):
        super().__init__()
        self._fix_loggers_level()
        self.s3_session: aioboto3.Session = aioboto3.Session()
        self.s3_api_key: str = os.getenv(S3Uploader.ENV_S3_API_KEY, None)
        self.s3_api_secret_key: str = os.getenv(S3Uploader.ENV_S3_API_SECRET_KEY, None)
        self.s3_endpoint_url: str = os.getenv(S3Uploader.ENV_S3_ENDPOINT_URL, None)
        self.s3_bucket_name: str = os.getenv(S3Uploader.ENV_S3_BUCKET_NAME, None)
        self.s3_region_name: str = os.getenv(S3Uploader.ENV_S3_REGION_NAME, None)
        if None in (self.s3_api_key, self.s3_api_secret_key, self.s3_endpoint_url,
                    self.s3_bucket_name, self.s3_region_name):
            raise TypeError("Some s3 environment variables are missing, please ensure that "
                            "S3_API_KEY, S3_API_SECRET_KEY, S3_BUCKET_NAME, S3_REGION_NAME "
                            "and S3_ENDPOINT_URL are defined.")

    @staticmethod
    def _fix_loggers_level():
        """
        Set aioboto3 and its components loggers level to Warning
        """
        logging.getLogger('aioboto3').setLevel(logging.WARNING)
        logging.getLogger('boto3').setLevel(logging.WARNING)
        logging.getLogger('botocore').setLevel(logging.WARNING)
        logging.getLogger('nose').setLevel(logging.WARNING)

    async def upload_file(self, upload_path: str, file_path: str, destination_file_name: str = None) -> int:
        """
        Upload file in s3
        :param upload_path: the upload path
        :param file_path: the file local path
        :param destination_file_name: the file name in s3 bucket (optional : default file_path basename)
        :return: the result of _upload
        """
        dest_file_name: str = destination_file_name \
            if destination_file_name is not None else os.path.basename(file_path)
        upload_file_url: str = f"{upload_path}{dest_file_name}"
        self.logger.info(f"Uploading {file_path} to s3 at {upload_file_url}...")
        return await self._upload(object_name=upload_file_url, local_file_path=file_path)

    async def upload_folder(self, upload_path: str, folder_path: str, destination_folder_name: str = None) -> int:
        """
        Upload recursive folder content in s3
        :param upload_path: the upload path
        :param folder_path: the folder local path
        :param destination_folder_name: the folder name in s3 bucket (optional : default folder_path basename)
        :return: the sum of all of _upload returns
        """
        dest_folder_name: str = destination_folder_name \
            if destination_folder_name is not None else os.path.basename(folder_path)
        upload_folder_url: str = f"{upload_path}{dest_folder_name}"
        return await self._upload_folder_content(upload_folder_url, folder_path)

    async def _upload_folder_content(self, upload_folder_url: str, folder_path: str) -> int:
        """
        Upload folder content in s3
        :param upload_folder_url: the folder upload path
        :param folder_path: the current folder path
        :return: the sum of all of _upload returns
        """
        error_count: int = 0
        for file_path in os.listdir(folder_path):
            if os.path.isdir(file_path):
                error_count += await self._upload_folder_content(upload_folder_url, folder_path)
            else:
                upload_file_url = f"{upload_folder_url}/{file_path}"
                self.logger.debug(f"Uploading {file_path} to s3 at {upload_file_url}...")
                error_count += await self._upload(object_name=upload_file_url,
                                                  local_file_path=os.path.join(folder_path, file_path))
        return error_count

    async def _upload(self, object_name: str, local_file_path: str) -> int:
        """
        Upload a file in the s3 bucket
        :param object_name: the object path
        :param local_file_path: the local file path
        :return: 0 if upload succeed else 1
        """
        async with self.s3_session.client(service_name=self.S3_BOTO_KEY,
                                          region_name=self.s3_region_name,
                                          endpoint_url=self.s3_endpoint_url,
                                          aws_access_key_id=self.s3_api_key,
                                          aws_secret_access_key=self.s3_api_secret_key) as s3:
            try:
                with open(local_file_path, 'rb') as file_content:
                    await s3.upload_fileobj(file_content, self.s3_bucket_name, object_name)
            except Exception as exception:
                self.logger.error(f"Failed to upload file on s3 bucket : {exception}")
                return 1
        return 0
