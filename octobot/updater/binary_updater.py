#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import enum
import json
import os
import stat

import aiofiles
import aiohttp

import octobot.commands as commands
import octobot.constants as constants
import octobot.updater.updater as updater_class
import octobot_commons.aiohttp_util as aiohttp_util
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.os_util as os_util


class DeliveryPlatformsName(enum.Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MAC = "osx"


class DeliveryPlatformsExtension(enum.Enum):
    WINDOWS = ".exe"
    LINUX = ""
    MAC = ""


class DeliveryArchitectureName(enum.Enum):
    X64_X86 = "x64"
    ARM_X64 = "arm_x64"


class BinaryUpdater(updater_class.Updater):
    BINARY_DELIVERY_SEPARATOR = "_"
    OLD_BINARY_SUFFIX = ".bak"
    NEW_BINARY_SUFFIX = ".new"

    async def get_latest_version(self):
        return self._parse_latest_version(await self._get_latest_release_data())

    async def update_impl(self) -> bool:
        # TODO fix binary updater to use release endpoint (assents can't be downloaded from gh directly)
        self.logger.error(f"Please manually update your OctoBot executable from this page: "
                          f"{self._get_latest_release_url(False)}")
        return False
        new_binary_file = await self._download_binary()
        if new_binary_file is not None:
            self._give_execution_rights(new_binary_file)
            self._move_binaries(commands.get_bot_file(), new_binary_file)
            return True
        return False

    def _get_latest_release_url(self, use_api_url):
        base = f"{commons_constants.GITHUB_API_CONTENT_URL}/repos" if use_api_url else commons_constants.GITHUB_BASE_URL
        return f"{base}/{commons_constants.GITHUB_ORGANISATION}/{constants.PROJECT_NAME}/releases/latest"

    async def _get_latest_release_data(self):
        try:
            async with aiohttp.ClientSession().get(self._get_latest_release_url(True)) as resp:
                text = await resp.text()
                if resp.status == 200:
                    return json.loads(text)
            return None
        except Exception as e:
            self.logger.debug(f"Error when fetching latest binary data : {e}")

    def _parse_latest_version(self, latest_release_data):
        try:
            if latest_release_data.get("draft", False) or latest_release_data.get("prerelease", False):
                return None
            else:
                return latest_release_data["tag_name"]
        except (KeyError, AttributeError) as e:
            self.logger.debug(f"Error when parsing latest binary version : {e}")
        return None

    async def _get_asset_from_release_data(self):
        latest_release_data = await self._get_latest_release_data()
        release_asset_name = self._create_release_asset_name(os_util.get_os())
        return release_asset_name, self._get_asset_from_name(latest_release_data, release_asset_name)

    def _get_asset_from_name(self, release_data, expected_asset_name):
        try:
            for asset in release_data["assets"]:
                if expected_asset_name == asset["name"]:
                    return asset
        except KeyError as e:
            self.logger.debug(f"Error when searching for {expected_asset_name} in latest release data : {e}")
        return None

    def _create_release_asset_name(self, platform):
        if platform is commons_enums.PlatformsName.WINDOWS:
            if os_util.is_machine_64bit():
                return f"{constants.PROJECT_NAME}{self.BINARY_DELIVERY_SEPARATOR}" \
                       f"{DeliveryPlatformsName.WINDOWS.value}{self.BINARY_DELIVERY_SEPARATOR}" \
                       f"{DeliveryArchitectureName.X64_X86.value}{DeliveryPlatformsExtension.WINDOWS.value}"
        elif platform is commons_enums.PlatformsName.MAC:
            if os_util.is_machine_64bit():
                if os_util.is_machine_64bit():
                    return f"{constants.PROJECT_NAME}{self.BINARY_DELIVERY_SEPARATOR}" \
                           f"{DeliveryPlatformsName.MAC.value}{self.BINARY_DELIVERY_SEPARATOR}" \
                           f"{DeliveryArchitectureName.X64_X86.value}{DeliveryPlatformsExtension.MAC.value}"
        elif platform is commons_enums.PlatformsName.LINUX:
            if os_util.is_machine_64bit():
                return f"{constants.PROJECT_NAME}{self.BINARY_DELIVERY_SEPARATOR}" \
                       f"{DeliveryPlatformsName.LINUX.value}{self.BINARY_DELIVERY_SEPARATOR}" \
                       f"{DeliveryArchitectureName.X64_X86.value}{DeliveryPlatformsExtension.LINUX.value}"
            elif os_util.is_arm_machine():
                return f"{constants.PROJECT_NAME}{self.BINARY_DELIVERY_SEPARATOR}" \
                       f"{DeliveryPlatformsName.LINUX.value}{self.BINARY_DELIVERY_SEPARATOR}" \
                       f"{DeliveryArchitectureName.ARM_X64.value}{DeliveryPlatformsExtension.LINUX.value}"
        return None

    async def _download_binary(self):
        release_asset_name, matching_asset_binary = await self._get_asset_from_release_data()
        new_binary_file = f"{release_asset_name}{self.NEW_BINARY_SUFFIX}"
        new_binary_file_url = matching_asset_binary["browser_download_url"]
        if matching_asset_binary is None:
            self.logger.error(f"Error when downloading latest version binary : Release not found on server")
            return None
        self.logger.info(f"Start downloading OctoBot update at {new_binary_file_url}")
        async with aiofiles.open(new_binary_file, 'wb+') as downloaded_file:
            await aiohttp_util.download_stream_file(output_file=downloaded_file,
                                                    file_url=new_binary_file_url,
                                                    aiohttp_session=aiohttp.ClientSession(),
                                                    is_aiofiles_output_file=True)
        self.logger.info(f"OctoBot update downloaded successfully")
        return new_binary_file

    def _move_binaries(self, current_binary_file, new_binary_file):
        self.logger.info(f"Updating local binary file")
        old_binary_path = f"{current_binary_file}{self.OLD_BINARY_SUFFIX}"
        try:
            os.remove(old_binary_path)
        except OSError:
            self.logger.debug(f"{old_binary_path} doesn't exist")
        os.rename(current_binary_file, old_binary_path)
        os.rename(new_binary_file, current_binary_file)

    def _give_execution_rights(self, new_binary_file):
        if os_util.get_os() is not commons_enums.PlatformsName.WINDOWS:
            self.logger.info(f"Adding execution rights to updated OctoBot binary")
            st = os.stat(new_binary_file)
            os.chmod(new_binary_file, st.st_mode | stat.S_IEXEC)
