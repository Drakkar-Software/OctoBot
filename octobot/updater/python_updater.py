#  Drakkar-Software OctoBot
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
import subprocess
from shlex import quote as shlex_quote

import aiohttp
import sys
from packaging.version import parse

import octobot.constants as constants
import octobot.updater.updater as updater_class


class PythonUpdater(updater_class.Updater):
    def __init__(self):
        super().__init__()
        self.use_git = False  # TODO

    async def get_latest_version(self):
        if self.use_git:
            return None
        # with pip
        return self._get_latest_pypi_version_from_data(await self._get_latest_pypi_version_data())

    def _get_latest_pypi_release_url(self):
        return f"https://pypi.python.org/pypi/{constants.PROJECT_NAME}/json"

    async def _get_latest_pypi_version_data(self):
        try:
            async with aiohttp.ClientSession().get(self._get_latest_pypi_release_url()) as resp:
                text = await resp.text()
                if resp.status == 200:
                    return json.loads(text)
            return None
        except Exception as e:
            self.logger.debug(f"Error when fetching latest pypi package data : {e}")

    def _get_latest_pypi_version_from_data(self, pypi_package_data):
        try:
            releases = pypi_package_data.get('releases', [])
            version = parse('0')
            for release in releases:
                ver = parse(release)
                if not ver.is_prerelease:
                    version = max(version, ver)
            return version
        except Exception as e:
            self.logger.debug(f"Failed to parse pypi package version : {e}")
            return None

    async def update_impl(self) -> bool:
        if self.use_git:
            return False
        try:
            # with pip
            self._run_pip_update_package(constants.PROJECT_NAME)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.debug(f"Failed to update pip package : {e}")
            return False

    def _run_pip_command(self, *args):
        """
        Use a shell-escaped version of sys.executable with pip module
        :param args: the pip args
        :return: the command result
        """
        return subprocess.check_output([shlex_quote(sys.executable), "-m", "pip", *args], shell=True)

    def _run_pip_install(self, *args):
        return self._run_pip_command(["install", "--prefer-binary", *args])

    def _run_pip_install_package(self, package_name):
        return self._run_pip_install([package_name])

    def _run_pip_update_package(self, package_name):
        return self._run_pip_install(["-U", package_name])

    def _run_pip_install_requirements_file(self, requirement_file):
        return self._run_pip_install(["-r", requirement_file])
