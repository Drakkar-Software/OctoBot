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


import sys
import os
import platform

from config import PLATFORM_DATA_SEPARATOR, OctoBotTypes, PlatformsName


def get_current_platform():
    # return examples:
    #   windows: 'Windows:10:AMD64'
    #   linux: 'Linux:4.15.0-46-generic:x86_64'
    #   rasp: 'Linux:4.14.98-v7+:armv7l'
    return f"{platform.system()}{PLATFORM_DATA_SEPARATOR}{platform.release()}{PLATFORM_DATA_SEPARATOR}" \
        f"{platform.machine()}"


def get_octobot_type():
    try:
        execution_arg = sys.argv[0]
        # sys.argv[0] is always the name of the python script called when using a command "python xyz.py"
        if execution_arg.endswith(".py"):
            if _is_on_docker():
                return OctoBotTypes.DOCKER.value
            else:
                return OctoBotTypes.PYTHON.value
        # sys.argv[0] is the name of the binary when using a binary version: ends with nothing or .exe"
        return OctoBotTypes.BINARY.value
    except IndexError:
        return OctoBotTypes.BINARY.value


def get_os():
    return PlatformsName(os.name)


def _is_on_docker():
    file_to_check = '/proc/self/cgroup'
    try:
        return (
            os.path.exists('/.dockerenv') or
            (os.path.isfile(file_to_check) and any('docker' in line for line in open(file_to_check)))
        )
    except FileNotFoundError:
        return False
