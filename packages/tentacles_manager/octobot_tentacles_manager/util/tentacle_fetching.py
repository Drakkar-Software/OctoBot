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
import aiofiles
import zipfile
import os
import os.path as path
import shutil

import octobot_commons.logging as commons_logging
import octobot_commons.aiohttp_util as aiohttp_util
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util as util

DOWNLOADED_DATA_CHUNK_SIZE = 60000


async def fetch_and_extract_tentacles(
    tentacles_temp_dir, tentacles_path_or_url, aiohttp_session, merge_dirs=False, hide_url=False
):
    compressed_file = tentacles_path_or_url
    should_download = _is_url(tentacles_path_or_url)
    try:
        if should_download:
            if aiohttp_session is None:
                raise RuntimeError("Missing aiohttp_session argument")
            compressed_file = f"downloaded_{tentacles_temp_dir}"
            last_modified = await _download_tentacles(compressed_file, tentacles_path_or_url, aiohttp_session)
            await util.log_tentacles_file_details(compressed_file, last_modified)
        await _extract_tentacles(compressed_file, tentacles_temp_dir, merge_dirs)
    except Exception as err:
        commons_logging.get_logger("TentaclesFetching").warning(
            f"Error when fetching tentacles from {'***' if hide_url else tentacles_path_or_url}: "
            f"{'' if hide_url else err} ({err.__class__.__name__})"
        )
        raise
    finally:
        if should_download and path.isfile(compressed_file):
            os.remove(compressed_file)


def cleanup_temp_dirs(target_path):
    if path.exists(target_path):
        shutil.rmtree(target_path)


def get_local_arch_download_path():
    return f"{util.get_os_str()}/{util.get_arch_str()}"


async def _download_tentacles(target_file, download_URL, aiohttp_session):
    async with aiofiles.open(target_file, 'wb+') as downloaded_file:
        return await aiohttp_util.download_stream_file(
            output_file=downloaded_file,
            file_url=download_URL,
            aiohttp_session=aiohttp_session,
            data_chunk_size=DOWNLOADED_DATA_CHUNK_SIZE,
            is_aiofiles_output_file=True
        )


async def _extract_tentacles(source_path, target_path, merge_dirs):
    if path.exists(target_path) and path.isdir(target_path) and not merge_dirs:
        shutil.rmtree(target_path)
    with zipfile.ZipFile(source_path) as zipped_tentacles:
        for archive_member in zipped_tentacles.namelist():
            if _is_tentacle_valid_tentacle_file(archive_member):
                zipped_tentacles.extract(archive_member, target_path)


def _is_tentacle_valid_tentacle_file(archive_member):
    member_path = archive_member.split("/")
    return len(member_path) >= 2 \
        and member_path[0] == constants.TENTACLES_ARCHIVE_ROOT \
        and (member_path[1] in constants.TENTACLE_TYPES or member_path[1] == constants.TENTACLES_PACKAGE_PROFILES_PATH)


def _is_url(string):
    return string.startswith("https://") \
           or string.startswith("http://") \
           or string.startswith("ftp://") \
           or string.startswith("sftp://")
