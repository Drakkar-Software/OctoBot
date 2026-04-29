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
import zipfile

import aiofiles
import aiohttp
import time

import pytest
import pytest_asyncio

import octobot_tentacles_manager.api.uploader as uploader_api
import octobot_tentacles_manager.constants as constants

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

TEST_S3_DIRECTORY = "s3-tests"
TEST_S3_PATH = "tentacle-manager/"
TEST_S3_FILE_NAME = "test"


@pytest_asyncio.fixture
async def s3_tests():
    if os.path.exists(TEST_S3_DIRECTORY):
        shutil.rmtree(TEST_S3_DIRECTORY)
    os.mkdir(TEST_S3_DIRECTORY)
    yield
    if os.path.exists(TEST_S3_DIRECTORY):
        shutil.rmtree(TEST_S3_DIRECTORY)


async def test_upload_file(s3_tests):
    s3_test_file_name: str = f"{time.time_ns()}.json"
    local_file_name: str = os.path.join(TEST_S3_DIRECTORY, f"{TEST_S3_FILE_NAME}.json")

    # test upload file
    with open(local_file_name, "w") as test_file:
        test_file.write(json.dumps({'test-key': 1}))
    assert await uploader_api.upload_file_or_folder_to_s3(s3_path=TEST_S3_PATH,
                                                          artifact_path=local_file_name,
                                                          artifact_alias=s3_test_file_name) == 0
    # test download file
    downloaded_file_path: str = await download_file_from_s3(f"/{TEST_S3_PATH}{s3_test_file_name}",
                                                            "downloaded_file")

    with open(downloaded_file_path, "r") as downloaded_file:
        assert json.loads(downloaded_file.read()) == {
            'test-key': 1
        }


async def test_upload_folder(s3_tests):
    test_dir_path = os.path.join(TEST_S3_DIRECTORY, "test-dir", "test-sub-dir")
    os.makedirs(test_dir_path)

    s3_test_file_name: str = f"{time.time_ns()}/sub_{time.time_ns()}"
    local_file_name: str = os.path.join(test_dir_path, f"{TEST_S3_FILE_NAME}.json")
    local_zip_path: str = os.path.join(test_dir_path, f"{TEST_S3_FILE_NAME}")

    # test upload file
    with open(local_file_name, "w") as test_file:
        test_file.write(json.dumps({'test-key': 1}))
    shutil.make_archive(os.path.abspath(local_zip_path), constants.TENTACLES_PACKAGE_FORMAT, test_dir_path)
    assert await uploader_api.upload_file_or_folder_to_s3(s3_path=TEST_S3_PATH,
                                                          artifact_path=test_dir_path,
                                                          artifact_alias=s3_test_file_name) == 0
    # test download folder files
    downloaded_file_path: str = await download_file_from_s3(f"/{TEST_S3_PATH}{s3_test_file_name}/test.json",
                                                            "downloaded_test.json")
    downloaded_zip_path: str = await download_file_from_s3(f"/{TEST_S3_PATH}{s3_test_file_name}/test.zip",
                                                           "downloaded_test.zip")
    with open(downloaded_file_path, "r") as downloaded_file:
        assert json.loads(downloaded_file.read()) == {
            'test-key': 1
        }
    downloaded_zipfile = zipfile.ZipFile(downloaded_zip_path)
    downloaded_zipfile.testzip()


async def download_file_from_s3(file_url: str, local_file_name: str) -> str:
    aiohttp_session = aiohttp.ClientSession()
    downloaded_file_path: str = os.path.join(TEST_S3_DIRECTORY, local_file_name)
    resp = await aiohttp_session.get(f"{constants.OCTOBOT_ONLINE}{file_url}")
    assert resp.status == 200
    async with aiofiles.open(downloaded_file_path, mode='wb') as downloaded_file:
        await downloaded_file.write(await resp.read())
    await aiohttp_session.close()
    return downloaded_file_path
